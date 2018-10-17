import operator
from collections import OrderedDict
from functools import reduce

import guitarpro as gp
from mingus.core import scales, notes


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
        if track:
            if track.channel.instrument not in self.GUITARS_CODES:
                raise ValueError("Track is not a guitar instrument")
            self.name = track.name
            self.is_12_stringed = track.is12StringedGuitarTrack
            self.tuning = "".join(str(string)[0] for string in reversed(track.strings))
            self.measures = tuple(Measure(measure, self.tuning) for measure in track.measures)
        self.strings = tuple(String(i, note) for i, note in enumerate(tuning[::-1], start=1))

    def get_notes(self, notes_list):
        """Returns a set of note objects that matches with the given notes"""
        return {note for string in self.strings for note in string.get_notes(notes_list)}


class Lick:
    def __init__(self):
        self.notes = []
        self.start = self.end = None

    def is_subset(self, notes_list):
        return set(self.notes).issubset(set(notes_list))


class Measure:
    def __init__(self, measure, tuning):
        signature = measure.header.timeSignature
        self.time_signature = (signature.numerator, signature.denominator)
        self.marker = measure.marker.name if measure.marker else None
        self.beats = tuple(Beat(beat, tuning) for beat in measure.voices[0].beats)  # todo handle multiple voices


class Beat:
    def __init__(self, beat, tuning):
        self.chord = Chord(beat.effect.chord) if beat.effect.chord else None
        self.notes = tuple(Note(note.string, note.value, tuning[::-1][note.string - 1], note.effect)
                           for note in beat.notes)


class Note:
    def __init__(self, string, fret, string_tuning, effect=None):
        self.string = string
        self.fret = fret
        self.effects = effect
        string_value = notes.note_to_int(string_tuning)
        self.name = notes.int_to_note((string_value + fret) % 12)

    def __eq__(self, other):
        return notes.is_enharmonic(self.name, other.name)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(str(self.string) + str(self.fret))

    def __str__(self):
        return f"String: {self.string}. Fret: {self.fret}. Name: {self.name}"

    def __repr__(self):
        return self.__str__()

    def is_enharnmonic(self, note):
        return notes.is_enharmonic(self.name, note)


class Chord:
    def __init__(self, chord):
        self.name = getattr(chord, 'name', None)
        self.strings = getattr(chord, 'strings', None)
        self.type = getattr(chord, 'type', None)


class String:
    FRETS = 23

    def __init__(self, index, tuning):
        if not notes.is_valid_note(tuning):
            raise ValueError(f"Tuning {tuning} is invalid.")
        self.index = index
        self.tuning = tuning
        self.notes = tuple(Note(index, fret, tuning) for fret in range(self.FRETS))

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.notes[item].name
        else:
            return tuple(note for note in self.notes if note.is_enharnmonic(item))

    def __str__(self):
        return f"{self.tuning}"

    def get_notes(self, note_list):
        return tuple(n1 for n1 in self.notes if any(n1.is_enharnmonic(n2) for n2 in note_list))


class Form:
    SUPPORTED_SCALES = {
        scales.Ionian,
        scales.Dorian,
        scales.Phrygian,
        scales.Lydian,
        scales.Mixolydian,
        scales.Aeolian,
        scales.Locrian,
        scales.MinorPentatonic,
        scales.MajorPentatonic,
        scales.MinorBlues,
        scales.MajorBlues
    }
    _STRINGS = tuple(String(i, note) for i, note in enumerate('EBGDAE', start=1))
    ROOT_FORMS = OrderedDict({
        'C': (_STRINGS[1], _STRINGS[4]),
        'A': (_STRINGS[4], _STRINGS[2]),
        'G': (_STRINGS[2], _STRINGS[0], _STRINGS[5]),
        'E': (_STRINGS[0], _STRINGS[5], _STRINGS[3]),
        'D': (_STRINGS[3], _STRINGS[1]),
    })

    def __init__(self, key=None, scale=None, form=None):
        try:
            self.key = key
            self.scale = scale
            self.form = form
            self.roots = []
            self.notes = []
            if not key:
                return
            if scale not in self.SUPPORTED_SCALES:
                raise NotImplementedError(f'Supported scales: {self.SUPPORTED_SCALES}')
        except TypeError:
            raise TypeError(f"{scale} object is not a scale defined in mingus.core.scales.")
        except AttributeError:
            raise AttributeError(f"Form {form} is invalid.")
        self.calculate_shape()

    def __add__(self, other):
        result = Form()
        if self.key == other.key and self.scale == other.scale:
            result.key = self.key
            result.scale = self.scale
        result.notes = list(set(self.notes) | set(other.notes))
        return result

    def __radd__(self, other):
        return self.__add__(other)

    def __contains__(self, note):
        return note in self.notes

    def __str__(self):
        return str(self.notes)

    def calculate_shape(self, form_start=0):
        """
        Calculates the notes belonging to this shape. This is done as follows:
        Find the notes on the 6th string belonging to the scale, and pick the first one that is on a fret >= form_start.
        Then progressively build the scale, go to the next string if the distance between the start and the note is
        greater than 3 frets (the pinkie would have to stretch and it's easier to get that note going down a string).
        If by the end not all the roots are included in the form, call the function again and start on an higher fret.
        """
        self.notes = []
        self.roots = [next(note for note in self.ROOT_FORMS[self.form][0][self.key] if note.fret >= form_start)]
        self.roots.extend(next(note for note in string[self.key] if note.fret >= self.roots[0].fret)
                          for string in self.ROOT_FORMS[self.form][1:])
        scale_notes = self.scale(self.key).ascending()
        candidates = self._STRINGS[5].get_notes(scale_notes)
        # picks the first note that is inside the form
        self.notes.append(next(note for note in candidates if note.fret >= form_start))
        start = self.notes[0].fret
        for string in reversed(self._STRINGS):
            i = string.index
            if i == 1:
                # Removes notes on the low E below the one just found on the high E to keep shape symmetrical
                while self.notes[0].fret < start:
                    self.notes.pop(0)
                # checks if the low e is missing a note that we found on the high E
                removed = self.notes.pop()
                if self.notes[0].fret != removed.fret:
                    self.notes.insert(0, self._STRINGS[5].notes[removed.fret])
                # Copies the remaining part of the low E in the high E
                for note in (note for note in self.notes.copy() if note.string == 6):
                    self.notes.append(self._STRINGS[0].notes[note.fret])
                break
            for note in string.get_notes(scale_notes):
                if note.fret <= start:
                    continue
                # picks the note on the higher string that is closer to the current position of the index finger
                higher_string_note = min(self._STRINGS[i - 2].get_notes((note.name,)),
                                         key=lambda note: abs(start - note.fret))
                # A note is too far if the pinkie has to go more than 3 frets away from the index finger
                if note.fret - start > 3:
                    self.notes.append(higher_string_note)
                    start = higher_string_note.fret
                    break
                else:
                    self.notes.append(note)
        if not set(self.roots).issubset(set(self.notes)):
            self.calculate_shape(form_start + 1)

    def get_score(self, note):
        l, r = self.roots[0].fret, self.roots[-1].fret
        return (note.fret - l) * (r - note.fret)

    @classmethod
    def join_forms(cls, *args):
        return reduce(operator.add, *args)
