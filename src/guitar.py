import mingus.core.notes as notes


class String:
    FRETS = 24

    def __init__(self, note):
        if not notes.is_valid_note(note):
            raise ValueError(f"Note {note} is invalid.")
        self.tuning = note
        base = notes.note_to_int(note)
        self.frets = tuple(notes.int_to_note((base + i) % 12) for i in range(self.FRETS))

    def __str__(self):
        return f"{self.tuning}"


class Guitar:
    def __init__(self, tuning='EADGBE', is_12_string=False):
        strings = 6 * (1 + is_12_string)
        try:
            self.strings = {i: String(note) for i, note in enumerate(reversed(tuning), 1)}
        except ValueError:
            raise ValueError(f"Tuning {tuning} for guitar with {strings} is invalid")

    def __str__(self):
        return str({n: str(string) for n, string in self.strings.items()})
