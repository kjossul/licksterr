import logging
import re
from enum import Enum

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY, ENUM

logger = logging.getLogger(__name__)
db = SQLAlchemy()


class Scale(Enum):
    IONIAN = 0
    DORIAN = 1
    PHRYGIAN = 2
    LYDIAN = 3
    MIXOLYDIAN = 4
    AEOLIAN = 5
    LOCRIAN = 6
    MINOR_PENTATONIC = 7
    MAJOR_PENTATONIC = 8
    MINOR_BLUES = 9
    MAJOR_BLUES = 10


class FormName(Enum):
    C = 0
    A = 1
    G = 2
    E = 3
    D = 4


class Note(ENUM):
    def __init__(self):
        format_string = "S{:d}F{:02d}"
        self.FRETS = 30
        self.enums = tuple(format_string.format(string, fret)
                           for string in range(6, 0, -1) for fret in range(0, self.FRETS))
        super().__init__(*self.enums, name='note')

    def get_value(self, string, fret):
        i = abs(string-6) * self.FRETS + fret
        return self.enums[i]



class ArrayOfEnum(ARRAY):

    def bind_expression(self, bindvalue):
        return db.cast(bindvalue, self)

    def result_processor(self, dialect, coltype):
        super_rp = super(ArrayOfEnum, self).result_processor(
            dialect, coltype)

        def handle_raw_string(value):
            inner = re.match(r"^{(.*)}$", value).group(1)
            return inner.split(",") if inner else []

        def process(value):
            if value is None:
                return None
            return super_rp(handle_raw_string(value))

        return process


class FormLick(db.Model):
    __tablename__ = 'form_lick'
    __table_args__ = (
        db.ForeignKeyConstraint(('form_key', 'form_scale', 'form_name'),
                                ('form.key', 'form.scale', 'form.name')),
    )
    form_key = db.Column(db.Integer, primary_key=True)
    form_scale = db.Column(db.Enum(Scale), primary_key=True)
    form_name = db.Column(db.Enum(FormName), primary_key=True)
    lick_id = db.Column(db.Integer, db.ForeignKey('lick.id'), primary_key=True)
    licks = db.relationship("Lick")


class Form(db.Model):
    __tablename__ = 'form'

    key = db.Column(db.Integer, primary_key=True)
    scale = db.Column(db.Enum(Scale), primary_key=True)
    name = db.Column(db.Enum(FormName), primary_key=True)
    notes = db.Column(ArrayOfEnum(Note), nullable=False, unique=True)
    licks = db.relationship("FormLick")


class Lick(db.Model):
    __tablename__ = 'lick'

    id = db.Column(db.Integer, primary_key=True)
    notes = db.Column(ArrayOfEnum(Note), nullable=False, unique=True)


class Song(db.Model):
    __tablename__ = 'song'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    artist = db.Column(db.String)
    album = db.Column(db.String)
    year = db.Column(db.Integer)
    genre = db.Column(db.String)
    tab = db.Column(db.LargeBinary)
