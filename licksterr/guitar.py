import bisect
import operator
from collections import OrderedDict
from fractions import Fraction
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
        self.strings = (None,) + tuple(String(note) for note in tuning[::-1])
        if track:
            if track.channel.instrument not in self.GUITARS_CODES:
                raise ValueError("Track is not a guitar instrument")
            self.name = track.name
            self.is_12_stringed = track.is12StringedGuitarTrack
            self.tuning = "".join(str(string)[0] for string in reversed(track.strings))
            self.measures = tuple(Measure(measure) for measure in track.measures)

    def __iter__(self):
        for i in range(6, 0, -1):
            yield i, self.strings[i]

    def get_notes(self, notes_list):
        """Returns a set of note objects that matches with the given notes"""
        return {note for string in self.strings[1:] for note in string.get_notes(notes_list)}


class String:
    FRETS = 23

    def __init__(self, tuning):
        if not notes.is_valid_note(tuning):
            raise ValueError(f"Tuning {tuning} is invalid.")
        self.tuning_name = tuning
        self.tuning_value = notes.note_to_int(self.tuning_name)
        self.notes = tuple(notes.int_to_note((self.tuning_value + fret) % 12) for fret in range(self.FRETS))

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.notes[item]
        else:
            return self.get_notes([item])

    def __iter__(self):
        for fret, note in enumerate(self.notes):
            yield fret, note

    def __str__(self):
        return f"{self.tuning_name}"

    def get_notes(self, note_list):
        """Returns a list of fret positions that match the notes given as input"""
        return tuple(fret for fret, n1 in enumerate(self.notes) if any(notes.is_enharmonic(n1, n2) for n2 in note_list))


class Measure:
    def __init__(self, measure):
        signature = measure.header.timeSignature
        self.duration = Fraction(signature.numerator, signature.denominator.value)
        self.marker = measure.marker.name if measure.marker else None
        self.beats = tuple(Beat(beat) for beat in measure.voices[0].beats)  # todo handle multiple voices


class Beat:
    def __init__(self, beat):
        self.chord = Chord(beat.effect.chord) if beat.effect.chord else None
        self.duration = Fraction(1, beat.duration.value)
        self.notes = tuple((note.string, note.value) for note in beat.notes)


class Chord:
    def __init__(self, chord):
        self.name = getattr(chord, 'name', None)
        self.strings = getattr(chord, 'strings', None)
        self.type = getattr(chord, 'type', None)


class Lick:
    def __init__(self, notes_list=None, start=None, end=None, tuning='EADGBE'):
        self.notes = tuple(notes_list) if notes_list else tuple()
        self.start = start
        self.end = end
        self.strings = (None,) + tuple(String(note) for note in tuning[::-1])

    def __contains__(self, note):
        return note in self.notes

    def __str__(self):
        return str(self.notes)


class Form(Lick):
    def __init__(self, notes_list, key=None, scale=None, forms='', transpose=False):
        super().__init__(notes_list)
        self.key = key
        self.scale = scale
        self.forms = forms
        if transpose:
            # Copy-pastes this shape along the fretboard. 11 is escluded because a guitar goes just up the 22th fret
            self.notes = list(self.notes)
            for string, fret in notes_list:
                if fret < 11:
                    bisect.insort(self.notes, (string, fret + 12))
                elif fret > 11:
                    bisect.insort(self.notes, (string, fret - 12))
            self.notes = tuple(self.notes)

    def __add__(self, other):
        note_list = tuple(sorted(set(self.notes) | set(other.notes)))
        if self.key == other.key:
            scale = self.scale if self.scale == other.scale else None
            forms = self.forms + other.forms if self.scale else ''
            return Form(note_list, self.key, scale, forms)
        else:
            return Form(note_list)

    def __radd__(self, other):
        return self.__add__(other)

    def __hash__(self):
        return hash(''.join(repr(note) for note in self.notes))

    def __str__(self):
        return f"{self.key} {self.scale} {self.forms}"

    def contains(self, lick):
        return set(self.notes).issuperset(set(lick.notes))

    @classmethod
    def join_forms(cls, *args):
        return reduce(operator.add, *args)

    @classmethod
    def calculate_caged_form(cls, key, scale, form, form_start=0, transpose=False):
        """
        Calculates the notes belonging to this shape. This is done as follows:
        Find the notes on the 6th string belonging to the scale, and pick the first one that is on a fret >= form_start.
        Then progressively build the scale, go to the next string if the distance between the start and the note is
        greater than 3 frets (the pinkie would have to stretch and it's easier to get that note going down a string).
        If by the end not all the roots are included in the form, call the function again and start on an higher fret.
        """
        strings = (None,) + tuple(String(note) for note in 'EADGBE'[::-1])
        # Indexes of string for each root form
        root_forms = OrderedDict({
            'C': (2, 5),
            'A': (5, 3),
            'G': (3, 1, 6),
            'E': (1, 6, 4),
            'D': (4, 2),
        })
        l_string = root_forms[form][0]  # string that has the leftmost root
        r_strings = root_forms[form][1:]  # other strings
        notes_list = []
        roots = [next((l_string, fret) for fret in strings[l_string][key] if fret >= form_start)]
        roots.extend(next((string, fret) for fret in strings[string][key] if fret >= roots[0][1])
                     for string in r_strings)
        scale_notes = scale(key).ascending()
        candidates = strings[6].get_notes(scale_notes)
        # picks the first note that is inside the form
        notes_list.append(next((6, fret) for fret in candidates if fret >= form_start))
        start = notes_list[0][1]
        for i in range(6, 0, -1):
            string = strings[i]
            if i == 1:
                # Removes the note added on the high E and just copy-pastes the low E
                notes_list.pop()
                # Copies the remaining part of the low E in the high E
                for note, fret in ((s, fret) for s, fret in notes_list.copy() if s == 6):
                    notes_list.append((1, fret))
                break
            for fret in string.get_notes(scale_notes):
                if fret <= start:
                    continue
                # picks the note on the higher string that is closer to the current position of the index finger
                higher_string_fret = min(strings[i - 1].get_notes([string.notes[fret]]),
                                         key=lambda x: abs(start - x))
                # No note is present in a feasible position on the higher string.
                if higher_string_fret > fret:
                    return cls.calculate_caged_form(key, scale, form, form_start=form_start + 1, transpose=transpose)
                # A note is too far if the pinkie has to go more than 3 frets away from the index finger
                if fret - start > 3:
                    notes_list.append((i - 1, higher_string_fret))
                    start = higher_string_fret
                    break
                else:
                    notes_list.append((i, fret))
        if not set(roots).issubset(set(notes_list)):
            return cls.calculate_caged_form(key, scale, form, form_start=form_start + 1, transpose=transpose)
        return cls(notes_list, key, scale.__name__, form, transpose=transpose)
