import guitarpro as gp
from mingus.core import notes as notes


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


class Measure:
    def __init__(self, measure):
        self.time_signature = measure.header.timeSignature  # todo find useful values
        self.marker = getattr(measure.marker, 'name', None)
        self.beats = tuple(Beat(beat) for beat in measure.voices[0].beats)  # todo check this voices call


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
        self.name = chord.name
        self.strings = chord.strings
        self.type = chord.type


class String:
    FRETS = 24

    def __init__(self, note):
        if not notes.is_valid_note(note):
            raise ValueError(f"Note {note} is invalid.")
        self.tuning = note
        base = notes.note_to_int(note)
        self.frets = tuple(notes.int_to_note((base + i) % 12) for i in range(self.FRETS))

    def __getitem__(self, item):
        return self.frets[item]

    def __str__(self):
        return f"{self.tuning}"
