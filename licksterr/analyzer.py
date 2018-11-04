import logging
import os
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import guitarpro as gp
from flask import Blueprint, request, abort, current_app, jsonify
from mingus.core import notes
from werkzeug.utils import secure_filename

from licksterr.models import db, Song, Beat, Measure, Track, TrackMeasure, TrackNote
from licksterr.util import timing

logger = logging.getLogger(__name__)
analysis = Blueprint('analysis', __name__)

PROJECT_ROOT = Path(os.path.realpath(__file__)).parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ANALYSIS_FOLDER = os.path.join(ASSETS_DIR, "analysis")

ALLOWED_EXTENSIONS = {'gp3', 'gp4', 'gp5'}


@analysis.route('/upload', methods=['POST'])
def upload_file():
    if not request.files:
        logger.debug("Received upload request without files.")
        abort(400)
    for filename, file in request.files.items():
        if file and allowed_file(filename):
            filename = secure_filename(filename)
            dest = os.path.join(current_app.config['UPLOAD_DIR'], filename)
            file.save(dest)
            logger.info(f"{filename} successfully uploaded to {dest}.")
            parse_song(dest)
    return "OK"


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@analysis.route('/songs/<song_id>', methods=['GET'])
def get_song_info(song_id):
    song = Song.query.get(song_id)
    if not song:
        abort(404)
    return jsonify(song.to_dict())


@analysis.route('/tracks/<track_id>', methods=['GET'])
def get_track_info(track_id):
    match = int(request.args.get('match', default=1))
    track = Track.query.get(track_id)
    if not track:
        abort(404)
    return jsonify(track.to_dict(match=match))


@analysis.route('/measures/<measure_id>', methods=['GET'])
def get_measure_info(measure_id):
    measure = Measure.query.get(measure_id)
    if not measure:
        abort(404)
    return jsonify(measure.to_dict())


def parse_song(filename):
    # todo avoid analysis if song already exists in DB
    GUITARS_CODES = {
        24: "Nylon string guitar",
        25: "Steel string guitar",
        26: "Jazz Electric guitar",
        27: "Clean guitar",
        28: "Muted guitar",
        29: "Overdrive guitar",
        30: "Distortion guitar"
    }
    logger.info(f"Parsing song {filename}")
    song = gp.parse(filename)
    data = {
        "album": song.album,
        "artist": song.artist,
        "tempo": song.tempo,
        "title": song.title,
        "year": song.copyright if song.copyright else None
    }
    s = Song(**data)
    db.session.add(s)
    for track in song.tracks:
        if getattr(track.channel, 'instrument', None) in GUITARS_CODES:
            t = parse_track(s, track)
            s.tracks.append(t)
    db.session.commit()


@timing
def parse_track(song, track):
    """
    Iterates the track beat by beat and checks for matches
    """
    track_duration = 0
    tuning = [notes.note_to_int(str(string)[0]) for string in reversed(track.strings)]
    measure_match = defaultdict(list)  # measure: list of indexes the measure occupies in the track
    note_match = defaultdict(float)  # note: % of time this note occupies in the track
    for i, measure in enumerate(track.measures):
        beats, durations = [], []
        for beat in measure.voices[0].beats:  # fixme handle multiple voices
            beat = Beat.get_or_create(beat)
            beats.append(beat)
            # Updates duration of objects
            track_duration += Fraction(1 / beat.duration)
            for note in beat.notes:
                note_match[note] += Fraction(1 / beat.duration)
        measure = Measure.get_or_create(beats, tuning=tuning)
        measure_match[measure].append(i)
    # Calculates final duration values
    note_match.update({k: note_match[k] / track_duration for k in note_match.keys()})
    # Updates database objects
    track = Track(song_id=song.id, tuning=tuning)
    for measure, indexes in measure_match.items():
        match = len(indexes) / (i + 1)
        db.session.add(TrackMeasure(track=track, measure=measure, match=match, indexes=indexes))
    for note, match in note_match.items():
        db.session.add(TrackNote(track=track, note=note, match=match))
    return track


if __name__ == '__main__':
    pass
