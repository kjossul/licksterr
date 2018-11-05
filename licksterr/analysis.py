import hashlib
import logging
import os
from collections import defaultdict, deque
from fractions import Fraction
from pathlib import Path

import guitarpro as gp
from mingus.core import notes

from licksterr.models import db, Song, Beat, Measure, Track, TrackMeasure, KEYS
from licksterr.util import timing

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.path.realpath(__file__)).parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ANALYSIS_FOLDER = os.path.join(ASSETS_DIR, "analysis")

# fixme find right parameter tuning. Now I've set it such as analysis is done at the end of all song.
MAJOR_PROFILES = [5.0, 2.0, 3.5, 2.0, 4.5, 4.0, 2.0, 4.5, 2.0, 3.5, 1.5, 4.0]
MINOR_PROFILES = [5.0, 2.0, 3.5, 4.5, 2.0, 4.0, 2.0, 4.5, 3.5, 2.0, 1.5, 4.0]
KS_SECONDS = 1000  # amount of seconds used to split segments in krumhansl-schmuckler alg
KS_CHANGE_PENALTY = 0.75  # penalty for changing the key in the k-s alg


def parse_song(filename, tracks=None):
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
        data['hash'] = str(hashlib.sha256(f.read()).digest()[:16])
    s = Song.query.filter_by(hash=data['hash']).first()
    if s:
        logger.debug(f"Song with the same hash already found. All tracks parsed.")
        return s
    s = Song(**data)
    for i, track in enumerate(song.tracks):
        if not tracks or i in tracks:
            t = parse_track(s, track, song.tempo)
            s.tracks.append(t)
    db.session.add(s)
    db.session.commit()
    return s


@timing
def parse_track(song, track, tempo):
    """
    Iterates the track beat by beat and checks for matches
    """
    logger.info(f"Parsing track {track.name}")
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
        measure = Measure.get_or_create(beats)
        measure_match[measure].append(i)
        # k-s analysis
        # tempo is expressed in quarters per minute. When we reached a segment long enough, start key analysis
        if segment_duration * 4 * 60 / tempo >= KS_SECONDS or m is track.measures[-1]:
            result = krumhansl_schmuckler(note_durations)
            best_match = max(result, key=result.get)
            if not key_match:
                key_match.append(best_match)
            else:
                previous_key = result[key_match[-1]]
                if best_match != previous_key and previous_key <= result[best_match] * KS_CHANGE_PENALTY:
                    key_match.append(best_match)
            segment_duration = 0
            note_durations = [0] * 12
    # Updates database objects
    # fixme handle empty tab
    logger.debug(f"Found keys {key_match}")
    track = Track(song_id=song.id, tuning=tuning, keys=key_match)
    for measure, indexes in measure_match.items():
        tm = TrackMeasure(track=track, measure=measure, match=len(track.measures), indexes=indexes)
        db.session.add(tm)
        # Calculates matches of track against form given the keys
    for k in set(key_match):
        track.add_key(k)
    return track


def krumhansl_schmuckler(durations):
    key_match = defaultdict(float)  # {(key, major?): score}
    major_profiles = deque(MAJOR_PROFILES)
    minor_profiles = deque(MINOR_PROFILES)
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
