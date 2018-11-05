import hashlib
import logging
import os
import uuid
from collections import defaultdict, deque
from fractions import Fraction
from pathlib import Path

import guitarpro as gp
from flask import Blueprint, request, abort, current_app, jsonify
from mingus.core import notes
from sqlalchemy.exc import IntegrityError

from licksterr.models import db, Song, Beat, Measure, Track, TrackMeasure, KEYS
from licksterr.util import timing

logger = logging.getLogger(__name__)
analysis = Blueprint('analysis', __name__)

PROJECT_ROOT = Path(os.path.realpath(__file__)).parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ANALYSIS_FOLDER = os.path.join(ASSETS_DIR, "analysis")

KS_SECONDS = 2  # amount of seconds used to split segments in krumhansl-schmuckler alg
KS_CHANGE_PENALTY = 0.8  # penalty for changing the key in the k-s alg


@analysis.route('/upload', methods=['POST'])
def upload_file():
    if not request.files:
        logger.debug("Received upload request without files.")
        abort(400)
    for file in request.files.values():
        if file:
            extension = file.filename[-4:]
            if extension not in {'.gp3', 'gp4', '.gp5'}:
                abort(400)
            temp_dest = str(current_app.config['TEMP_DIR'] / str(uuid.uuid1()))
            file.save(temp_dest)
            logger.debug(f"temporarily uploaded to {temp_dest}.")
            try:
                song = parse_song(temp_dest)
                file.save(str(current_app.config['UPLOAD_DIR'] / (str(song.id))))
                logger.debug(f"Successfully parsed song {song}")
            except IntegrityError:
                logger.debug("Song already exists with the same hash")
                db.session.rollback()
            # todo check what happens if random file is uploaded
            os.remove(temp_dest)
            logger.debug("Removed file at temporary destination.")
    return "OK"


@analysis.route('/songs/<song_id>', methods=['GET'])
def get_song_info(song_id):
    song = Song.query.get(song_id)
    if not song:
        abort(404)
    return jsonify(song.to_dict())


@analysis.route('/tracks/<track_id>', methods=['GET'])
def get_track_info(track_id):
    track = Track.query.get(track_id)
    if not track:
        abort(404)
    return jsonify(track.to_dict())


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
        "year": song.copyright if song.copyright else None,
    }
    with open(filename, mode='rb') as f:
        data['hash'] = hashlib.sha256(f.read()).digest()[:16]
    s = Song(**data)
    db.session.add(s)
    found_keys = set()
    for track in song.tracks:
        if getattr(track.channel, 'instrument', None) in GUITARS_CODES:
            t, key_match = parse_track(s, track, song.tempo)
            s.tracks.append(t)
            found_keys.update(key_match)
    s.keys = found_keys
    db.session.commit()
    return s


@timing
def parse_track(song, track, tempo):
    """
    Iterates the track beat by beat and checks for matches
    """
    tuning = [notes.note_to_int(str(string)[0]) for string in track.strings]
    measure_match = defaultdict(list)  # measure: list of indexes the measure occupies in the track
    key_match = []  # {key: list of keys found}
    note_durations = [0] * 12
    segment_duration = 0
    for i, m in enumerate(track.measures):
        beats, durations = [], []
        for beat in m.voices[0].beats:  # fixme handle multiple voices
            beat = Beat.get_or_create(beat)
            beats.append(beat)
            # k-s analysis
            beat_duration = Fraction(1 / beat.duration)
            for note in beat.notes:
                note_value = (tuning[note.string - 1] + note.fret) % 12
                note_durations[note_value] += beat_duration
            # Does not increment segment duration if we had just pauses since now
            if any(duration for duration in note_durations):
                segment_duration += beat_duration
        measure = Measure.get_or_create(beats, tuning=tuning)
        measure_match[measure].append(i)
        # k-s analysis
        # tempo is expressed in quarters per minute. When we reached a segment long enough, start key analysis
        if segment_duration * 4 * 60 / tempo >= KS_SECONDS or m is track.measures[-1]:
            result = krumhansl_schmuckler(note_durations)
            best_match = max(result, key=result.get)
            if not key_match:
                key_match.append(best_match)
            else:
                if result[key_match[-1]] <= result[best_match] * KS_CHANGE_PENALTY:
                    key_match.append(best_match)
            segment_duration = 0
            note_durations = [0] * 12
    # Updates database objects
    track = Track(song_id=song.id, tuning=tuning)
    for measure, indexes in measure_match.items():
        match = len(indexes) / (i + 1)
        db.session.add(TrackMeasure(track=track, measure=measure, match=match, indexes=indexes))
    return track, key_match


def krumhansl_schmuckler(durations):
    key_match = defaultdict(float)  # {(key, major?): score}
    major_profiles = deque([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profiles = deque([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    for i in range(12):
        key_match[KEYS.index((i, True))] = dot(durations, major_profiles)
        key_match[KEYS.index((i, False))] = dot(durations, minor_profiles)
        major_profiles.rotate(1)
        minor_profiles.rotate(1)
    return key_match


def dot(l1, l2):
    if len(l1) != len(l2):
        return 0
    return sum(i[0] * i[1] for i in zip(l1, l2))


if __name__ == '__main__':
    pass
