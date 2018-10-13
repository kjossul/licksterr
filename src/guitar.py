from collections import defaultdict, OrderedDict

import guitarpro as gp
from mingus.core import intervals
from mingus.core import notes


class Song:
    def __init__(self, filename, guitar_cls=None):
        guitar_cls = guitar_cls if guitar_cls else Guitar
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

    def __init__(self, track=None, tuning='EADGBE'):
        self.tuning = tuning
        if track:
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

    def get_notes(self, ns):
        """Returns a set of (string, fret) pairs that match with the given notes"""
        ns = tuple(n for n in ns) if not isinstance(ns, str) else (ns,)
        out = set()
        for i, string in self.strings.items():
            out.update({(i, n) for n in string.get_notes(ns)})
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
    FRETS = 23

    def __init__(self, note):
        if not notes.is_valid_note(note):
            raise ValueError(f"Note {note} is invalid.")
        self.tuning = note
        base = notes.note_to_int(note)
        self.notes = tuple(notes.int_to_note((base + i) % 12) for i in range(self.FRETS))

    def get_notes(self, ns):
        ns = ns if not isinstance(ns, str) else {ns}
        return tuple(i for i, n1 in enumerate(self.notes) if any(notes.is_enharmonic(n1, n2) for n2 in ns))

    def __getitem__(self, item):
        return self.notes[item]

    def __str__(self):
        return f"{self.tuning}"


class Form:
    # todo make this tuning-dependent. A form depends on the tuning and is part of the guitar.
    FORMS = OrderedDict({
        'C': {'left': 2, 'right': 5, 'width': 2},
        'A': {'left': 5, 'right': 3, 'width': 2},
        'G': {'left': 3, 'right': 1, 'width': 3},
        'E': {'left': 1, 'right': 4, 'width': 2},
        'D': {'left': 4, 'right': 2, 'width': 3},
    })
    GUITAR = Guitar()

    def __init__(self, key, scale, form, octave=0):
        """octave is the index of the octave to choose (0 means the leftmost)"""
        try:
            self.key = key
            self.scale = scale
            self.form = form
            scale_notes = scale(key).ascending()
            root_forms = self.get_root_forms(key, form)
            # Keeps the first position if we have finished the fretboard
            roots = root_forms[octave] if len(root_forms) > octave else root_forms[octave-1]
            self.notes = [(i, note) for i, string in self.GUITAR.strings.items()
                          for note in string.get_notes(scale_notes) if roots[0][1] - 2 <= note <= roots[-1][1] + 1]
            # todo remove notes that should be out of the boxes
        except TypeError:
            raise TypeError(f"{scale} object is not a scale defined in mingus.core.scales.")
        except AttributeError:
            raise AttributeError(f"Form {form} is invalid.")

    @classmethod
    def get_root_forms(cls, key, form):
        form = cls.FORMS[form]
        l, r, w = form['left'], form['right'], form['width']
        left = cls.GUITAR.strings[l].get_notes(key)
        right = tuple(l + w for l in left)
        out = []
        for n1, n2 in zip(left, right):
            r = form['right']
            if r == 1:  # G form
                out.append(((l, n1), (1, n2), (6, n2)))
            elif l == 1:  # E form
                out.append(((1, n1), (6, n1), (r, n2)))
            else:  # C, A, D forms have just two notes
                out.append(((l, n1), (r, n2)))
        return out
