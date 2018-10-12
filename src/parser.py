import guitarpro as gp
from src.guitar import Guitar


class Analyzer:
    def __init__(self, filename):
        song = gp.parse(filename)
        self.guitars = tuple(Guitar.from_track(GuitarTrack(track))
                              for track in song.tracks if track.channel.instrument in GuitarTrack.GUITARS)


class GuitarTrack:
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


class Measure:
    def __init__(self, measure):
        self.time_signature = measure.header.timeSignature  # todo find useful values
        self.marker = getattr(measure.marker, 'name', None)
        self.beats = tuple(Beat(beat) for beat in measure.voices[0].beats)  # todo check this voices call


class Beat:
    def __init__(self, beat):
        self.chord = beat.effect.chord  # todo find usage
        self.notes = tuple(Note(note) for note in beat.notes)


class Note:
    def __init__(self, note):
        self.string = note.string
        self.value = note.value
        self.effects = note.effect
