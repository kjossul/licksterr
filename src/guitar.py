import mingus.core.notes as notes
from collections import defaultdict


class String:
    FRETS = 24

    def __init__(self, note):
        if not notes.is_valid_note(note):
            raise ValueError(f"Note {note} is invalid.")
        self.tuning = note
        base = notes.note_to_int(note)
        self.frets = tuple(notes.int_to_note((base + i) % 12) for i in range(self.FRETS))
        self.notes = defaultdict(lambda: defaultdict(int))  # {measure: {beat: value}}

    def count_hits(self):
        out = defaultdict(int)
        for beat in self.notes.values():
            for v in beat.values():
                out[v] += 1
        return out

    def __str__(self):
        return f"{self.tuning}"


class Guitar:
    def __init__(self, name='Guitar', tuning='EADGBE', is_12_stringed=False):
        self.name = name
        strings = 6 * (1 + is_12_stringed)
        try:
            self.strings = {i: String(note) for i, note in enumerate(reversed(tuning), 1)}
        except ValueError:
            raise ValueError(f"Tuning {tuning} for guitar with {strings} is invalid")

    @classmethod
    def from_track(cls, track):
        instance = cls(track.name, track.tuning, track.is_12_stringed)
        for i, measure in enumerate(track.measures):
            for j, beat in enumerate(measure.beats):
                for note in beat.notes:
                    instance.strings[note.string].notes[i][j] = note.value
        return instance

    def __str__(self):
        return str({n: str(string) for n, string in self.strings.items()})
