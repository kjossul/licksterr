import logging
from enum import Enum
from fractions import Fraction

from flask_sqlalchemy import SQLAlchemy
from guitarpro import NoteType
from mingus.core import notes, scales
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.mutable import MutableList

from licksterr.util import row2dict

logger = logging.getLogger(__name__)
db = SQLAlchemy()


class ScaleEnum(Enum):
    IONIAN = 0
    DORIAN = 1
    PHRYGIAN = 2
    LYDIAN = 3
    MIXOLYDIAN = 4
    AEOLIAN = 5
    LOCRIAN = 6
    MINORPENTATONIC = 7
    MAJORPENTATONIC = 8
    MINORBLUES = 9
    MAJORBLUES = 10


class FormEnum(Enum):
    CAGED = 0
    # todo calculations of the forms should be easy enough that a method called everytime a scale is requested should
    # be sufficient to calculate them in a reasonable amount of time
    THREE_NOTE_PER_STRING = 1
    SEGOVIA = 2


NOTES_DICT = {notes.int_to_note(value, accidental): value for value in range(12) for accidental in ('#', 'b')}

KEYS = tuple((value, is_major) for is_major in (True, False) for value in range(12))

SCALES_DICT = {
    # scale to enum
    scales.Ionian: ScaleEnum.IONIAN,
    scales.Dorian: ScaleEnum.DORIAN,
    scales.Phrygian: ScaleEnum.PHRYGIAN,
    scales.Lydian: ScaleEnum.LYDIAN,
    scales.Mixolydian: ScaleEnum.MIXOLYDIAN,
    scales.Aeolian: ScaleEnum.AEOLIAN,
    scales.Locrian: ScaleEnum.LOCRIAN,
    scales.MinorPentatonic: ScaleEnum.MINORPENTATONIC,
    scales.MajorPentatonic: ScaleEnum.MAJORPENTATONIC,
    scales.MinorBlues: ScaleEnum.MINORBLUES,
    scales.MajorBlues: ScaleEnum.MAJORBLUES,
}

ENUM_DICT = {
    # enum to scale
    ScaleEnum.IONIAN: scales.Ionian,
    ScaleEnum.DORIAN: scales.Dorian,
    ScaleEnum.PHRYGIAN: scales.Phrygian,
    ScaleEnum.LYDIAN: scales.Lydian,
    ScaleEnum.MIXOLYDIAN: scales.Mixolydian,
    ScaleEnum.AEOLIAN: scales.Aeolian,
    ScaleEnum.LOCRIAN: scales.Locrian,
    ScaleEnum.MINORPENTATONIC: scales.MinorPentatonic,
    ScaleEnum.MAJORPENTATONIC: scales.MajorPentatonic,
    ScaleEnum.MINORBLUES: scales.MinorBlues,
    ScaleEnum.MAJORBLUES: scales.MajorBlues
}
# True for major scales, False for minor scales
SCALES_TYPE = {
    True: [ScaleEnum.MAJORPENTATONIC, ScaleEnum.IONIAN, ScaleEnum.LYDIAN, ScaleEnum.MIXOLYDIAN, ScaleEnum.MAJORBLUES],
    False: [ScaleEnum.MINORPENTATONIC, ScaleEnum.AEOLIAN, ScaleEnum.DORIAN, ScaleEnum.PHRYGIAN, ScaleEnum.LOCRIAN,
            ScaleEnum.MINORBLUES]
}
STANDARD_TUNING = (4, 11, 7, 2, 9, 4)
FLOAT_PRECISION = 5


class String:
    FRETS = 23

    def __init__(self, tuning):
        if not 0 <= tuning < 12:
            raise ValueError(f"Tuning must be an integer in [0, 11].")
        self.notes = tuple(notes.int_to_note((tuning + fret) % 12) for fret in range(self.FRETS))

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.notes[item]
        else:
            return self.get_notes([item])

    def __iter__(self):
        for fret, note in enumerate(self.notes):
            yield fret, note

    def __str__(self):
        return str(self.notes)

    def get_notes(self, note_list):
        """Returns a list of fret positions that match the notes given as input"""
        return tuple(fret for fret, n1 in self if any(notes.is_enharmonic(n1, n2) for n2 in note_list))


class Tuning(db.Model):
    __tablename__ = 'tuning'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    value = db.Column(db.ARRAY(db.Integer))

    scales = db.relationship('Scale')
    tracks = db.relationship('Track')

    def __str__(self):
        return f"{self.name} - {self.value}"

    def __getitem__(self, item):
        return self.value[item]

    @classmethod
    def get_by_value(cls, tuning):
        return cls.query.filter_by(value=tuning).first()


class Scale(db.Model):
    """
    Models the layout of a scale on the guitar fretboard. All the forms are stored relative to the C key, luckily for
    the guitar we can just transpose the shape to obtain a different key.
    """
    __tablename__ = 'scale'
    __table_args__ = (
        db.UniqueConstraint('name', 'tuning_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    tuning_id = db.Column(db.Integer, db.ForeignKey('tuning.id'), nullable=False)
    name = db.Column(db.Enum(ScaleEnum), nullable=False)
    intervals = db.Column(ARRAY(db.Integer), unique=True)
    is_major = db.Column(db.Boolean, nullable=False)

    tracks = association_proxy('scale_to_track', 'track')

    def __init__(self, scale, tuning, **kwargs):
        intervals = [notes.note_to_int(note) for note in scale('C').ascending()]
        super().__init__(name=SCALES_DICT[scale], tuning_id=tuning.id, intervals=intervals,
                         is_major=SCALES_DICT[scale] in SCALES_TYPE[True], **kwargs)

    def get_notes(self, key=0):
        tuning = Tuning.query.get(self.tuning_id)
        return (note for note in Note.get_all_notes()
                if (note.get_int_value(tuning.value) - key) % 12 in self.intervals)


class Chord(db.Model):
    __tablename__ = 'chord'

    id = db.Column(db.Integer, primary_key=True)
    # todo


class Song(db.Model):
    __tablename__ = 'song'

    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String(128), unique=True)
    key = db.Column(db.Integer)
    album = db.Column(db.String())
    artist = db.Column(db.String())
    title = db.Column(db.String())
    tempo = db.Column(db.Integer)
    year = db.Column(db.Integer)
    extension = db.Column(db.String(3))
    tracks = db.relationship('Track', backref=db.backref("song"), cascade='all,delete')

    def __str__(self):
        return f"{self.artist} - {self.title}"

    def to_dict(self):
        info = row2dict(self)
        info['tracks'] = [track.id for track in self.tracks]
        return info


class Track(db.Model):
    __tablename__ = 'track'

    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('song.id', ondelete='CASCADE'), nullable=False)
    tuning_id = db.Column(db.Integer, db.ForeignKey('tuning.id', ondelete='CASCADE'), nullable=False)
    index = db.Column(db.Integer)  # Index of the track in the song
    keys = db.Column(ARRAY(db.Integer))

    scales = association_proxy('track_to_scale', 'scale')
    measures = association_proxy('track_to_measure', 'measure')
    notes = association_proxy('track_to_note', 'note')

    def __str__(self):
        song = Song.query.get(self.song_id)
        return f"Track #{self.id} for song {song}"

    def to_dict(self, key=None):
        key = key if key else self.keys[0]
        info = row2dict(self)
        scale_matches = ScaleTrack.get_track_matches(self)
        best_match = scale_matches[0]
        # TODO return all requested scales
        info['scale'] = best_match
        info['key'] = key
        return info

    def calculate_scale_matches(self, key):
        is_major = key < 12
        key_value = key % 12
        for scale in SCALES_TYPE[is_major]:
            match = 0
            s = Scale.query.filter_by(tuning_id=self.tuning_id, name=scale).first()
            for note in s.get_notes(key):
                tn = TrackNote.query.get((self.id, note.id))
                match += tn.match if tn else 0
            st = ScaleTrack(scale=s, track=self, key=key_value, match=match)
            db.session.add(st)

    def get_form_match(self):
        return {}


class Measure(db.Model):
    __tablename__ = 'measure'

    id = db.Column(db.Integer, primary_key=True)
    repr = db.Column(db.String(), nullable=False, unique=True)
    forms = association_proxy('measure_to_form', 'form')
    beats = association_proxy('measure_to_beat', 'beat')

    def __str__(self):
        return self.repr

    def to_dict(self):
        info = row2dict(self)
        info['beats'] = []
        for association in MeasureBeat.query.filter_by(measure=self).all():
            info['beats'].append({**association.beat.to_dict(), **{'indexes': association.indexes}})
        return info

    @classmethod
    def get_or_create(cls, beats):
        """
        Retrieves the measure with the given beats or creates a new one from them. Upon creation, known forms in the
        database are matched against the notes found in each beat and % of matching is calculated.
        """
        id_string = ''.join(beat.id for beat in beats)
        measure = Measure.query.filter_by(repr=id_string).first()
        if not measure:
            measure = Measure(repr=id_string)
            db.session.add(measure)
            total_duration = 0
            for i, beat in enumerate(beats):
                mb = MeasureBeat.get(measure, beat)
                if not mb:
                    db.session.add(MeasureBeat(measure=measure, beat=beat, indexes=[i]))
                else:
                    mb.indexes.append(i)
                beat_duration = Fraction(1 / beat.duration)
                if beat.notes:
                    total_duration += beat_duration
        return measure


class Beat(db.Model):
    __tablename__ = 'beat'

    id = db.Column(db.String(33), primary_key=True)  # 39 max length (6 notes * 5 ('SxFyy') + 3 ('Dzz'))
    duration = db.Column(db.Integer, nullable=False)  # duration of the note(s) (1 - whole, 2 - half, ...)
    notes = association_proxy('beat_to_note', 'note')

    def to_dict(self):
        return {'duration': self.duration, 'notes': [note.to_dict() for note in self.notes]}

    @classmethod
    def get_or_create(cls, beat, prev_beat=None):
        if len(beat.notes) > 6:
            raise ValueError("Can't have more than two notes per string!")
        ns = []
        if not beat.notes:  # Pause beat
            ns.append((Note.get(-1, 0), False))
        else:
            for note in beat.notes:
                if note.type == NoteType.tie and prev_beat:
                    try:
                        ns.append((next(prev_note for prev_note in prev_beat.notes
                                        if note.string - 1 == prev_note.string), True))
                    except StopIteration:
                        logger.debug(f"Found tie to non-marked note at measure {beat.voice.measure.number} on string "
                                     f"{note.string} (skipping).")
                else:
                    ns.append((Note.get(note.string - 1, note.value, muted=note.type == NoteType.dead), False))
        id = ''.join(repr(note) for note, _ in ns) + f'D{beat.duration.value:02}'
        b = Beat.query.get(id)
        if not b:
            b = Beat(id=id, duration=beat.duration.value)
            db.session.add(b)
            for note, tie in ns:
                db.session.add(BeatNote(beat=b, note=note, tie=tie))
        return b


class Note(db.Model):
    __tablename__ = 'note'
    __table_args__ = (
        db.UniqueConstraint('string', 'fret'),
    )

    id = db.Column(db.Integer, primary_key=True)
    string = db.Column(db.Integer, nullable=False)
    fret = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"S{self.string}F{self.fret:02}"

    def to_dict(self):
        return row2dict(self)

    def get_int_value(self, tuning=STANDARD_TUNING):
        return (tuning[self.string] + self.fret) % 12

    def equals_string_and_pitch(self, other):
        return self.string == other.string and abs(self.fret - other.fret) % 12 == 0

    def is_pause(self):
        return self.string == -1

    @classmethod
    def get(cls, string, fret, muted=False):
        fret = fret if not muted else -1  # -1 encodes the muted note (X)
        return cls.query.filter_by(string=string, fret=fret).first()

    @classmethod
    def get_all_notes(cls):
        """
        :return: All notes in the database that represent a valid note (not muted or the pause note)
        """
        return (note for note in cls.query.all() if note.fret >= 0 and note.string >= 0)


# Associations

class ScaleTrack(db.Model):
    __tablename__ = 'scale_track'

    track_id = db.Column(db.Integer, db.ForeignKey('track.id', ondelete='cascade'), primary_key=True)
    scale_id = db.Column(db.Integer, db.ForeignKey('scale.id', ondelete='cascade'), primary_key=True)
    key = db.Column(db.Integer, nullable=False)
    match = db.Column(db.Float(precision=FLOAT_PRECISION))

    scale = db.relationship('Scale', backref=db.backref("scale_to_track", cascade='all, delete-orphan'))
    track = db.relationship('Track', backref=db.backref("track_to_scale", cascade='all, delete-orphan'))

    @classmethod
    def get_track_matches(cls, track):
        return [{"name": x.scale.name.name, "key": x.key, "match": x.match, "is_major": x.scale.is_major} for x in
                sorted(cls.query.filter_by(track=track).all(), key=lambda x: x.match, reverse=True)]


class TrackMeasure(db.Model):
    __tablename__ = 'track_measure'

    track_id = db.Column(db.Integer, db.ForeignKey('track.id', ondelete='cascade'), primary_key=True)
    measure_id = db.Column(db.Integer, db.ForeignKey('measure.id', ondelete='cascade'), primary_key=True)
    # % that this measure occupies in the track
    match = db.Column(db.Float(precision=FLOAT_PRECISION))
    indexes = db.Column(MutableList.as_mutable(ARRAY(db.INTEGER)))

    track = db.relationship('Track', backref=db.backref("track_to_measure", cascade='all, delete-orphan'))
    measure = db.relationship('Measure', backref=db.backref("measure_to_track", cascade='all, delete-orphan'))

    def __str__(self):
        return f"Match (track: {self.track}, measure: {self.measure}): {self.match}"

    @classmethod
    def get_measures(cls, track):
        return cls.query.filter_by(track=track).all()


class TrackNote(db.Model):
    __tablename__ = 'track_note'

    track_id = db.Column(db.Integer, db.ForeignKey('track.id', ondelete='cascade'), primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id', ondelete='cascade'), primary_key=True)
    # % that this note occupies in the track
    match = db.Column(db.Float(precision=FLOAT_PRECISION))

    track = db.relationship('Track', backref=db.backref("track_to_note", cascade='all, delete-orphan'))

    @classmethod
    def get_or_create(cls, track, note, match=0):
        tn = cls.query.get((track.id, note.id))
        if not tn:
            tn = TrackNote(track=track, note_id=note.id, match=match)
        return tn


class MeasureBeat(db.Model):
    __tablename__ = 'measure_beat'

    measure_id = db.Column(db.Integer, db.ForeignKey('measure.id'), primary_key=True)
    beat_id = db.Column(db.String(39), db.ForeignKey('beat.id'), primary_key=True)
    indexes = db.Column(MutableList.as_mutable(ARRAY(db.INTEGER)))

    measure = db.relationship('Measure', backref=db.backref('measure_to_beat', cascade='all, delete-orphan'))
    beat = db.relationship('Beat', backref=db.backref('beat_to_measure', cascade='all, delete-orphan'))

    @classmethod
    def get(cls, measure, beat):
        return cls.query.get((measure.id, beat.id))


class BeatNote(db.Model):
    __tablename__ = 'beat_note'

    beat_id = db.Column(db.String(39), db.ForeignKey('beat.id'), primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), primary_key=True)
    tie = db.Column(db.Boolean)
    # todo store not effect here
    # relationships
    beat = db.relationship('Beat', backref=db.backref('beat_to_note', cascade='all, delete-orphan'))
    note = db.relationship('Note', backref=db.backref('note_to_beat', cascade='all, delete-orphan'))
