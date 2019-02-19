import logging
import os
import struct
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import guitarpro as gp
from guitarpro import NoteType
from mingus.core import notes

from licksterr.exceptions import BadTabException
from licksterr.key_finder import KeyFinderAggregator
from licksterr.models import db, Song, Beat, Measure, Track, TrackMeasure
from licksterr.util import timing

logger = logging.getLogger(__name__)


def parse_song(file, tracks=None, extension="", hash="", title="", artist=""):
    try:
        file.seek(0)
        song = gp.parse(file)
    except struct.error:
        raise BadTabException("Cannot open tab file.")
    data = {
        "album": song.album,
        "artist": artist if artist else song.artist,
        "tempo": song.tempo,
        "title": title if title else song.title,
        "year": song.copyright if song.copyright else None,
        "extension": extension,
        "hash": hash
    }
    s = Song.query.filter_by(hash=data['hash']).first()
    if s:
        logger.debug(f"Song with the same hash already found.")
        return s
    s = Song(**data)
    logger.info(f"Parsing song {s}")
    for i, track in enumerate(song.tracks):
        if not tracks or i in tracks:
            t = parse_track(s, track, i)
            s.tracks.append(t)
    db.session.add(s)
    db.session.commit()
    return s


@timing
def parse_track(song, track, index):
    """
    Iterates the track beat by beat and checks for matches
    """
    logger.info(f"Parsing track {track.name}")
    tuning = [notes.note_to_int(str(string)[0]) for string in track.strings]
    measure_match = defaultdict(list)  # measure: list of indexes the measure occupies in the track
    finder = KeyFinderAggregator()
    note_durations = [0] * 12
    segment_duration = 0
    prev_beat = None  # used to correctly store tied note information
    for i, m in enumerate(track.measures):
        beats = []
        for b in m.voices[0].beats:  # fixme handle multiple voices
            beat = Beat.get_or_create(b, prev_beat=prev_beat)
            beats.append(beat)
            prev_beat = beat
            # k-s analysis
            beat_duration = Fraction(1 / beat.duration)
            for note in b.notes:
                if note.string > 0 and note.type != NoteType.dead:  # if it's not a pause beat
                    note_value = (tuning[note.string - 1] + note.value) % 12
                    note_durations[note_value] += beat_duration
            # Does not increment segment duration if we had just pauses since now
            if any(duration for duration in note_durations):
                segment_duration += beat_duration
        measure = Measure.get_or_create(beats)
        measure_match[measure].append(i)
        # k-s analysis
        # tempo is expressed in quarters per minute. When we reached a segment long enough, start key analysis
        # if segment_duration * 4 * 60 / tempo >= KS_SECONDS or m is track.measures[-1]:
        # Current implementation: make analysis at the end of each measure. (segment_duration not used)
        finder.insert_durations(note_durations)
        segment_duration = 0
        note_durations = [0] * 12
    # Updates database objects
    # Calculates matches of track against form given the keys
    results = finder.get_results()
    track = Track(song_id=song.id, tuning=tuning, keys=[], index=index)
    for measure, indexes in measure_match.items():
        tm = TrackMeasure(track=track, measure=measure, match=len(track.measures), indexes=indexes)
        db.session.add(tm)
    for k in set(results):
        track.add_key(k)
    return track


if __name__ == '__main__':
    pass
