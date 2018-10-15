import copy
from collections import defaultdict, OrderedDict

import guitarpro as gp
from mingus.core import intervals, scales
from mingus.core import notes

from src.exceptions import FormShapeError


class Song:
    def __init__(self, filename, guitar_cls=None):
        guitar_cls = guitar_cls if guitar_cls else Guitar
        song = gp.parse(filename)
        self.guitars = tuple(Guitar.from_track(GuitarTrack(track))
                              for track in song.tracks if track.channel.instrument in GuitarTrack.GUITARS)


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
            self.measures = tuple(Measure(measure) for measure in track.measures)
        self.strings = OrderedDict({i: String(note) for i, note in enumerate(reversed(self.tuning), 1)})

    def yield_sounds(self):
        for measure in self.measures:
            for beat in measure.beats:
                if beat.chord:
                    yield Chord(beat.chord)
                elif beat.notes:
                    yield beat.notes
                else:  # todo yield a pause after some time (at least one measure?) has passed
                    pass

    def calculate_intervals(self, form=None):
        out, prev = defaultdict(int), None
        for sound in self.yield_sounds():
            # if a chord is encountered or the sound is outside the box shape it is considered a stop
            if isinstance(sound, Chord) or (form and not form.includes_all(note for note in sound)):
                prev = None
            else:
                curr = [self.strings[note.string][note.value] for note in
                        sorted(sound, key=lambda note:note.string, reverse=True)]
                for interval in self.determine_intervals(prev, curr):
                    out[interval] += 1
                prev = curr
        return out

    def determine_intervals(self, notes1, notes2):
        if not notes1 or not notes2:
            return set()
        return (intervals.determine(n1, n2, shorthand=True) for n1, n2 in zip(notes1, notes2))

    def get_notes(self, ns):
        """Returns a set of (string, fret) pairs that match with the given notes"""
        ns = tuple(n for n in ns) if not isinstance(ns, str) else (ns,)
        return {i: string.get_notes(ns) for i, string in self.strings.items()}


class Measure:
    def __init__(self, measure):
        signature = measure.header.timeSignature
        self.time_signature = (signature.numerator, signature.denominator)
        self.marker = measure.marker.name if measure.marker else None
        self.beats = tuple(Beat(beat) for beat in measure.voices[0].beats)  # todo handle multiple voices


class Beat:
    def __init__(self, beat):
        self.chord = Chord(beat.effect.chord) if beat.effect.chord else None
        self.notes = tuple(Note(note) for note in beat.notes)


class Note:
    def __init__(self, note):
        self.string = note.string
        self.value = note.value
        self.effects = note.effect


class Chord:
    def __init__(self, chord):
        self.name = getattr(chord, 'name', None)
        self.strings = getattr(chord, 'strings', None)
        self.type = getattr(chord, 'type', None)


class String:
    FRETS = 23

    def __init__(self, note):
        if not notes.is_valid_note(note):
            raise ValueError(f"Note {note} is invalid.")
        self.tuning = note
        base = notes.note_to_int(note)
        self.notes = tuple(notes.int_to_note((base + i) % 12) for i in range(self.FRETS))

    def get_notes(self, ns):
        ns = ns if not isinstance(ns, str) else {ns}  # allows calls with strings
        return tuple(i for i, n1 in enumerate(self.notes) if any(notes.is_enharmonic(n1, n2) for n2 in ns))

    def __getitem__(self, item):
        return self.notes[item]

    def __str__(self):
        return f"{self.tuning}"


class Form:
    SUPPORTED = {
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
    FORMS = OrderedDict({
        'C': {'left': 2, 'right': 5, 'width': 2},
        'A': {'left': 5, 'right': 3, 'width': 2},
        'G': {'left': 3, 'right': 1, 'width': 3},
        'E': {'left': 1, 'right': 4, 'width': 2},
        'D': {'left': 4, 'right': 2, 'width': 3},
    })
    GUITAR = Guitar()

    def __init__(self, key, scale, form):
        try:
            self.key = key
            self.scale = scale
            self.form = form
            scale_notes = scale(key).ascending()
            if scale not in self.SUPPORTED:
                raise NotImplementedError(f'Supported scales: {self.SUPPORTED}')
        except TypeError:
            raise TypeError(f"{scale} object is not a scale defined in mingus.core.scales.")
        except AttributeError:
            raise AttributeError(f"Form {form} is invalid.")
        try:
            self.calculate_shape(form, key, scale_notes)
        except FormShapeError:
            self.calculate_shape(form, key, scale_notes, octave=1)

    def calculate_shape(self, form, key, scale_notes, octave=0):
        self.roots = self.get_form_roots(key, form, octave=octave)
        self.notes = defaultdict(list)
        pos = self.GUITAR.strings[6].get_notes(scale_notes)
        candidates = (n1 for n1, n2 in zip(pos[:-1], (pos[0],) + pos[:-2]) if n2 - n1 != 1)
        # picks the first note that has a decent score to start searching for others
        if self.scale in (scales.MajorPentatonic, scales.MinorPentatonic) or \
                self.form == 'C' and self.scale in (scales.Lydian, scales.MajorBlues):
            min_score = -3  # a score of -3 is a fret down in the shapes of E, C and A
        else:
            min_score = 0
        self.notes[6].append(next(note for note in candidates if self.get_score(note) >= min_score))
        start = self.notes[6][0] + 1
        for i, string in reversed(self.GUITAR.strings.items()):
            if i == 1:
                # makes the two E strings the same, including the last found note on the high string
                self.notes[6] = self.notes[1] + [note for note in self.notes[6] if note > self.notes[1][0]]
                self.notes[1] = self.notes[6].copy()
                break
            for note in (n for n in string.get_notes(scale_notes) if n >= start):
                # picks the note on the higher string that is closer to the current position of the index finger
                higher_string_note = min(self.GUITAR.strings[i - 1].get_notes(string[note]),
                                         key=lambda x: abs(self.notes[i][0] - x))
                # A note is too far if the pinkie has to go more than 3 frets away from the finger
                is_far = note - self.notes[i][0] > 3
                if is_far:
                    # if this note is easier to get by going up a string do that
                    if abs(self.notes[i][0] - higher_string_note) <= note - self.notes[i][0]:
                        self.notes[i - 1].append(higher_string_note)
                        start = higher_string_note + 1
                        break
                    else:
                        raise FormShapeError  # can't find an easy shape, need to move up in octaves
                else:
                    self.notes[i].append(note)

    def get_score(self, note):
        l, r = min(self.roots.values()), max(self.roots.values())
        return (note - l) * (r - note)

    @classmethod
    def get_form_roots(cls, key, form, octave=0):
        """Gets all the roots for the given form and key"""
        form = cls.FORMS[form]
        l, r, w = form['left'], form['right'], form['width']
        left = min(cls.GUITAR.strings[l].get_notes(key)) + octave * 12
        right = left + w
        if r == 1:  # G form
            return {l: left, 1: right, 6: right}
        elif l == 1:  # E form
            return {1: left, 6: left, r: right}
        else:  # C, A, D forms have just two notes
            return {l: left, r: right}

    def includes_all(self, ns):
        return all(note.value in self.notes[note.string] for note in ns)

    def __add__(self, other):
        result = copy.copy(self)
        result.roots = result.form = None
        if self.key != other.key:
            result.key = None
        if self.scale != other.scale:
            result.scale = None
        result.notes = {i: sorted(set(self.notes[i] + other.notes[i])) for i in self.notes.keys()}
        return result

    def __radd__(self, other):
        return self.__add__(other)

    def __str__(self):
        return str(self.notes)