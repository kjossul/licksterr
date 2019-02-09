import hashlib
import json
import os
import struct

import guitarpro as gp
from flask import Blueprint, request, current_app, jsonify, abort

from licksterr.analysis import parse_song, logger
from licksterr.exceptions import BadTabException
from licksterr.models import Song, Track, Measure
from licksterr.models import db
from licksterr.util import flask_file_handler, OK

song = Blueprint('song', __name__)


@song.route('/upload', methods=['POST'])
@flask_file_handler
def upload_file(file, temp_file):
    tracks = request.values.get('tracks', None)
    tracks = json.loads(tracks) if tracks else None
    try:
        content = temp_file.read()
        temp_file.seek(0)
        h = str(hashlib.sha256(content).digest()[:16])
        s = parse_song(temp_file, tracks=[int(track) for track in tracks], extension=file.filename[-3:], hash=h)
        with open(str(current_app.config['UPLOAD_DIR'] / (str(s.id))), mode="wb") as f:
            f.write(content)
    except BadTabException:
        abort(400)
    logger.debug(f"Successfully parsed song {s}")
    return OK


@song.route('/tabinfo', methods=['POST'])
@flask_file_handler
def get_tab_info(file, temp_file):
    try:
        song = gp.parse(temp_file)
    except struct.error:
        abort(400)
    return jsonify({i: track.name for i, track in enumerate(song.tracks) if len(track.strings) == 6})


@song.route('/songs/<song_id>', methods=['GET'])
def get_song(song_id):
    song = Song.query.get(song_id)
    if not song:
        abort(404)
    return jsonify(song.to_dict())


@song.route('/tracks/<track_id>/keys/<key_id>', methods=['PUT'])
def add_track_key(track_id, key_id):
    Track.query.get(track_id).add_key(key_id)
    db.session.commit()
    return OK


@song.route('/tracks/<track_id>/keys/<key_id>', methods=['DELETE'])
def remove_track_key(track_id, key_id):
    Track.query.get(track_id).remove_key(key_id)
    db.session.commit()
    return OK


@song.route('/songs/<song_id>', methods=['DELETE'])
def remove_song(song_id):
    song = Song.query.get(song_id)
    if not song:
        abort(404)
    db.session.delete(song)
    os.remove(current_app.config['UPLOAD_DIR'] / str(song_id))
    logger.debug("Removed file on disk.")
    db.session.commit()
    return OK


@song.route('/tracks/<track_id>', methods=['GET'])
def get_track(track_id):
    track = Track.query.get(track_id)
    if not track:
        abort(404)
    return jsonify(track.to_dict())


@song.route('/measures/<measure_id>', methods=['GET'])
def get_measure(measure_id):
    measure = Measure.query.get(measure_id)
    if not measure:
        abort(404)
    return jsonify(measure.to_dict())
