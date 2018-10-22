import logging
import os
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import guitarpro as gp
from mingus.core import notes

from licksterr.models import db, Song, Beat, Measure, Track, TrackMeasure, TrackNote

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.path.realpath(__file__)).parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ANALYSIS_FOLDER = os.path.join(ASSETS_DIR, "analysis")
FORMS_DB = os.path.join(ANALYSIS_FOLDER, "forms.json")


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
    song = gp.parse(filename)
    data = {
        "album": song.album,
        "artist": song.artist,
        "tempo": song.tempo,
        "title": song.title,
        "year": song.copyright
    }
    s = Song(**data)
    db.session.add(s)
    tracks = tuple(parse_track(s, track) for track in song.tracks
                   if getattr(track.channel, 'instrument', None) in GUITARS_CODES)
    s.tracks.extend(tracks)
    db.session.commit()


def parse_track(song, track):
    """
    Iterates the track beat by beat todo doc
    """
    track_duration = 0
    tuning = (notes.note_to_int(str(string)[0]) for string in reversed(track.strings))
    measure_match = defaultdict(float)  # measure: % of time this measure occupies in the track
    note_match = defaultdict(float)  # note: % of time this note occupies in the track
    for measure in track.measures:
        beats, durations = [], []
        if len(measure.voices > 1):
            raise NotImplementedError("Multiple voices not yet supported")
        for beat in measure.voices[0].beats:
            beat = Beat.get_or_create(beat)
            beats.append(beat)
            # Updates duration of objects
            track_duration += Fraction(1 / beat.duration)
            for note in beat.notes:
                note_match[note] += Fraction(1 / beat.duration)
        measure = Measure.get_or_create(beats, tuning=tuning)
        measure_match[measure] += 1
    # Calculates final duration values
    measure_match.update({k: measure_match[k] / len(track.measures) for k in measure_match.keys()})
    note_match.update({k: note_match[k] / track_duration for k in note_match.keys()})
    # Updates database objects
    track = Track(song_id=song.id, tuning=tuning)
    for measure, match in measure_match.items():
        db.session.add(TrackMeasure(track=track, measure=measure, match=match))
    for note, match in note_match.items():
        db.session.add(TrackNote(track=track, note=note, match=match))
    return track


if __name__ == '__main__':
    pass
