import hashlib
import logging
import os
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import guitarpro as gp
from mingus.core import notes

from licksterr.key_finder import KeyFinder
from licksterr.models import db, Song, Beat, Measure, Track, TrackMeasure
from licksterr.util import timing

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.path.realpath(__file__)).parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ANALYSIS_FOLDER = os.path.join(ASSETS_DIR, "analysis")

KS_SECONDS = 1.5  # amount of seconds used to split segments in krumhansl-schmuckler alg


def parse_song(filename, tracks=None):
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
        logger.debug(f"Song with the same hash already found.")
        return s
    s = Song(**data)
    logger.info(f"Parsing song {s}")
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
    keyfinder = KeyFinder()
    note_durations = [0] * 12
    segment_duration = 0
    for i, m in enumerate(track.measures):
        beats = []
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
        # if segment_duration * 4 * 60 / tempo >= KS_SECONDS or m is track.measures[-1]:
        # Current implementation: make analysis at the end of each measure.
        keyfinder.insert_durations(note_durations)
        segment_duration = 0
        note_durations = [0] * 12
    # Updates database objects
    # fixme handle empty tab
    track = Track(song_id=song.id, tuning=tuning, keys=[])
    for measure, indexes in measure_match.items():
        tm = TrackMeasure(track=track, measure=measure, match=len(track.measures), indexes=indexes)
        db.session.add(tm)
    # Calculates matches of track against form given the keys
    results = keyfinder.get_results()
    for k in set(results):
        track.add_key(k)
    return track


if __name__ == '__main__':
    pass
