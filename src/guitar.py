from collections import defaultdict, OrderedDict

import guitarpro as gp
from mingus.core import intervals
from mingus.core import notes


class Song:
    def __init__(self, filename):
        song = gp.parse(filename)
        self.guitars = tuple(Guitar.from_track(GuitarTrack(track))
                              for track in song.tracks if track.channel.instrument in GuitarTrack.GUITARS)


class Guitar:
    GUITARS = {
        24: "Nylon string guitar",
        25: "Steel string guitar",
        26: "Jazz Electric guitar",
        27: "Clean guitar",
        28: "Muted guitar",
        29: "Overdrive guitar",
        30: "Distortion guitar"
    }

    def __init__(self, track):
        if track.channel.instrument not in self.GUITARS:
            raise ValueError("Track is not a guitar instrument")
        self.name = track.name
        self.is_12_stringed = track.is12StringedGuitarTrack
        self.tuning = "".join(str(string)[0] for string in reversed(track.strings))
        self.measures = tuple(Measure(measure) for measure in track.measures)
        self.strings = {i: String(note) for i, note in enumerate(reversed(self.tuning), 1)}

    def yield_sounds(self, pattern=None):
        # todo yield only notes in particular pattern / shapes (i.e. positions on the fretboard)
        for measure in self.measures:
            for beat in measure.beats:
                if len(beat.notes) > 1:  # if a beat contains more than one note is considered a separator
                    yield Chord(beat.chord)
                elif len(beat.notes) is 1:
                    note = beat.notes[0]
                    yield self.strings[note.string][note.value]

    def calculate_intervals(self, pattern=None):
        out, prev = defaultdict(int), None
        for sound in self.yield_sounds(pattern=pattern):
            if isinstance(sound, Chord):
                prev = None
            else:
                if prev:
                    interval = intervals.determine(prev, sound, shorthand=True)
                    out[interval] += 1
                prev = sound
        return out

    def get_notes(self, note):
        """Returns a set of (string, fret) pairs that match with the given note"""
        out = set()
        for i, string in self.strings.items():
            out.update({(i, n) for n in string.get_notes(note)})
        return out


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
    FRETS = 24

    def __init__(self, note):
        if not notes.is_valid_note(note):
            raise ValueError(f"Note {note} is invalid.")
        self.tuning = note
        base = notes.note_to_int(note)
        self.notes = tuple(notes.int_to_note((base + i) % 12) for i in range(self.FRETS))

    def get_notes(self, note):
        return {i for i, n in enumerate(self.notes) if n == note}

    def __getitem__(self, item):
        return self.notes[item]

    def __str__(self):
        return f"{self.tuning}"


class Form:
    FORMS = OrderedDict({
        'C': {'notes': {(2, 0), (5, 2)}, 'width': 2},
        'A': {'notes': {(5, 0), (3, 2)}, 'width': 2},
        'G': {'notes': {(3, 0), (1, 3), (6, 3)}, 'width': 3},
        'E': {'notes': {(1, 0), (6, 0), (4, 2)}, 'width': 2},
        'D': {'notes': {(4, 0), (2, 3)}, 'width': 3},
    })

    def __init__(self, form):
        try:
            self.notes = self.FORMS[form]['notes']
        except IndexError:
            raise ValueError(f'{form} is not a valid form')

    @classmethod
    def chain(cls, form, start=0, end=String.FRETS):
        """Chains together all the forms starting from the given form and fret"""
        roots = set()
        caged = "CAGED" * 3
        for form in caged[caged.index(form):]:
            for note in cls.FORMS[form]['notes']:
                if note[1] + start < end:
                    roots.add((note[0], note[1] + start))
            start += cls.FORMS[form]['width']
        return roots
