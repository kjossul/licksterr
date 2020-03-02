import logging
import struct
from collections import defaultdict
from fractions import Fraction

import guitarpro as gp
from mingus.core import notes

from licksterr.exceptions import BadTabException
from licksterr.key_finder import KeyFinderAggregator
from licksterr.models import db, Song, Beat, Measure, Track, TrackMeasure, TrackNote, Tuning
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
    db.session.add(s)
    logger.info(f"Parsing song {s}")
    for i, track in enumerate(song.tracks):
        if not tracks or i in tracks:
            t = parse_track(s, track, i)
            s.tracks.append(t)
    db.session.commit()
    return s


@timing
def parse_track(song, track, index):
    """
    Iterates the track beat by beat and checks for matches
    """
    logger.info(f"Parsing track {track.name}")
    tuning = Tuning.get_by_value([notes.note_to_int(str(string)[0]) for string in track.strings])
    measure_match = defaultdict(list)  # measure: list of indexes the measure occupies in the track
    finder = KeyFinderAggregator()
    total_duration = 0
    measure_note_durations = [0] * 12
    segment_duration = 0
    prev_beat = None  # used to correctly store tied note information
    note_match = defaultdict(int)  # % a note occupies in the track (chords are treated as separated notes)
    for i, m in enumerate(track.measures, start=1):
        # fixme handle different durations based on bmp changes
        beats = []
        for b in m.voices[0].beats:  # fixme handle multiple voices
            beat = Beat.get_or_create(b, prev_beat=prev_beat)
            beats.append(beat)
            prev_beat = beat
            # k-s analysis
            beat_duration = Fraction(1 / beat.duration)
            for note in beat.notes:
                note_match[note] += beat_duration
                total_duration += beat_duration
                if not note.is_pause():
                    measure_note_durations[note.get_int_value()] += beat_duration
            # Does not increment segment duration if we had just pauses since now
            if any(duration for duration in measure_note_durations):
                segment_duration += beat_duration
        measure = Measure.get_or_create(beats)
        measure_match[measure].append(i)
        # k-s analysis
        # tempo is expressed in quarters per minute. When we reached a segment long enough, start key analysis
        # if segment_duration * 4 * 60 / tempo >= KS_SECONDS or m is track.measures[-1]:
        # Current implementation: make analysis at the end of each measure. (segment_duration not used)
        finder.insert_durations(measure_note_durations)
        segment_duration = 0
        measure_note_durations = [0] * 12
    total_measures = i
    note_match = {k: v / total_duration for k, v in note_match.items()}
    # Updates database objects
    # Calculates matches of track against form given the keys
    keys_found = finder.get_results()
    track = Track(song_id=song.id, tuning_id=tuning.id, keys=list(keys_found), index=index)
    for measure, indexes in measure_match.items():
        weight = len(indexes)
        tm = TrackMeasure(track=track, measure=measure, match=weight / total_measures, indexes=indexes)
        db.session.add(tm)
    for note, match in note_match.items():
        tn = TrackNote.get_or_create(track, note, match=float(match))
        db.session.add(tn)
    for k in set(keys_found):
        track.calculate_scale_matches(k)
    return track


if __name__ == '__main__':
    pass
