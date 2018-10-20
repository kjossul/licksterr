import logging
from enum import Enum

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY

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




class NoteContainer(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    notes = db.Column(ARRAY(db.Integer, dimensions=2), nullable=False)
    tuning = db.Column(ARRAY(db.Integer), nullable=False)

    def __init__(self, **kwargs):
        kwargs['tuning'] = kwargs.get('tuning', (4, 9, 2, 7, 11, 4))
        super().__init__(**kwargs)

    @classmethod
    def contains(cls, string, fret):
        return cls.notes.contains([[string, fret]])


class Form(NoteContainer):
    __tablename__ = 'form'
    __table_args__ = (
        db.UniqueConstraint('key', 'scale', 'name', 'tuning'),
    )

    key = db.Column(db.Integer)
    scale = db.Column(db.Enum(Scale))
    name = db.Column(db.String)
    licks = db.relationship("Lick", secondary=lambda: form_lick)


class Lick(NoteContainer):
    __tablename__ = 'lick'

    unique_key = db.Column(db.String, nullable=False, unique=True)
    forms = db.relationship("Form", secondary=lambda: form_lick)

    def __init__(self, **kwargs):
        note_list = kwargs['notes']
        kwargs['unique_key'] = ''.join(f"S{string}F{fret:02}" for string, fret in note_list)
        super().__init__(**kwargs)


# Helper table for Form-Lick many-to-many relationship
form_lick = db.Table('form_lick',
                     db.Column('form_id', db.Integer, db.ForeignKey("form.id"), primary_key=True),
                     db.Column('lick_id', db.Integer, db.ForeignKey("lick.id"), primary_key=True))


class Song(db.Model):
    __tablename__ = 'song'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    artist = db.Column(db.String)
    album = db.Column(db.String)
    year = db.Column(db.Integer)
    genre = db.Column(db.String)
    tab = db.Column(db.LargeBinary)
