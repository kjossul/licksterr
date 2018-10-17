import json
import operator
from functools import reduce

import guitarpro as gp
from mingus.core import notes


class Song:
    def __init__(self, filename, guitar_cls=None):
        guitar_cls = guitar_cls if guitar_cls else Guitar
        song = gp.parse(filename)
        self.data = {
            "album": song.album,
            "artist": song.artist,
            "year": song.copyright,
            "genre": song.tempoName,
            "title": song.title
        }
        self.tempo = song.tempo
        self.key = song.key
        self.guitars = tuple(guitar_cls(track=track) for track in song.tracks if track.channel.instrument)


class Guitar:
    GUITARS_CODES = {
        24: "Nylon string guitar",
        25: "Steel string guitar",
        26: "Jazz Electric guitar",
        27: "Clean guitar",
        28: "Muted guitar",
        29: "Overdrive guitar",
        30: "Distortion guitar"
    }

    def __init__(self, track=None, tuning='EADGBE'):
        self.tuning = tuning
        self.strings = tuple(String(i, note) for i, note in enumerate(tuning[::-1], start=1))
        if track:
            if track.channel.instrument not in self.GUITARS_CODES:
                raise ValueError("Track is not a guitar instrument")
            self.name = track.name
            self.is_12_stringed = track.is12StringedGuitarTrack
            self.tuning = "".join(str(string)[0] for string in reversed(track.strings))
            self.measures = tuple(Measure(measure, self.strings) for measure in track.measures)

    def get_notes(self, notes_list):
        """Returns a set of note objects that matches with the given notes"""
        return {note for string in self.strings for note in string.get_notes(notes_list)}


class String:
    FRETS = 23

    def __init__(self, index, tuning):
        if not notes.is_valid_note(tuning):
            raise ValueError(f"Tuning {tuning} is invalid.")
        self.index = index
        self.tuning = tuning
        self.notes = tuple(Note(index, fret, self.get_note_name(fret)) for fret in range(self.FRETS))

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.notes[item].name
        else:
            return tuple(note for note in self.notes if note.is_enharmonic(item))

    def __str__(self):
        return f"{self.tuning}"

    def get_notes(self, note_list):
        return tuple(n1 for n1 in self.notes if any(n1.is_enharmonic(n2) for n2 in note_list))

    def get_note_name(self, fret):
        string_value = notes.note_to_int(self.tuning)
        return notes.int_to_note((string_value + fret) % 12)


class Measure:
    def __init__(self, measure, strings):
        signature = measure.header.timeSignature
        self.time_signature = (signature.numerator, signature.denominator)
        self.marker = measure.marker.name if measure.marker else None
        self.beats = tuple(Beat(beat, strings) for beat in measure.voices[0].beats)  # todo handle multiple voices


class Beat:
    def __init__(self, beat, strings):
        self.chord = Chord(beat.effect.chord) if beat.effect.chord else None
        self.notes = tuple(
            Note(note.string, note.value, strings[note.string - 1].get_note_name(note.value), note.effect)
            for note in beat.notes)


class Note:
    def __init__(self, string, fret, name, effect=None):
        self.string = string
        self.fret = fret
        self.effect = effect
        self.name = name

    def __eq__(self, other):
        return self.is_enharmonic(other.name)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(str(self.string) + str(self.fret))

    def __str__(self):
        return f"String: {self.string}. Fret: {self.fret}. Name: {self.name}"

    def __repr__(self):
        return self.__str__()

    def is_enharmonic(self, note):
        return notes.is_enharmonic(self.name, note)

    def get_octave(self):
        """Returns the other note on the same string with the same name."""
        fret = self.fret - 12 if self.fret >= 12 else self.fret + 12
        return Note(self.string, fret, self.name)

    def to_json(self):
        return json.dumps((self.string, self.fret, self.name))

    @classmethod
    def from_json(cls, s):
        data = json.loads(s)
        return cls(*data)


class Chord:
    def __init__(self, chord):
        self.name = getattr(chord, 'name', None)
        self.strings = getattr(chord, 'strings', None)
        self.type = getattr(chord, 'type', None)


class Lick:
    def __init__(self, notes_list=None, start=None, end=None):
        self.notes = notes_list if notes_list else tuple()
        self.start = start
        self.end = end

    def __contains__(self, note):
        return note in self.notes

    def __str__(self):
        return str(self.notes)

    def is_subset(self, other):
        return set(self.notes).issubset(set(other.notes))


class Form(Lick):
    def __init__(self, notes_list, key=None, scale=None, forms='', transpose=False):
        super().__init__(notes_list)
        self.key = key
        self.scale = scale
        self.forms = forms
        if transpose:
            # Copy-pastes this shape along the fretboard. 11 is escluded because a guitar goes just up the 22th fret
            self.notes.extend(note.get_octave() for note in self.notes.copy() if note.fret != 11)

    def __add__(self, other):
        note_list = tuple(set(self.notes) | set(other.notes))
        if self.key == other.key:
            scale = self.scale if self.scale == other.scale else None
            forms = self.forms + other.forms if self.scale else ''
            return Form(note_list, self.key, scale, forms)
        else:
            return Form(note_list)

    def __radd__(self, other):
        return self.__add__(other)

    @classmethod
    def join_forms(cls, *args):
        return reduce(operator.add, *args)
