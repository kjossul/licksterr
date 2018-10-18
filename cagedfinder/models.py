import logging
from enum import Enum

from flask_sqlalchemy import SQLAlchemy

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


class NoteSequence(db.Model):
    __tablename__ = 'note_sequences'
    __table_args__ = (
        db.ForeignKeyConstraint(['note_string', 'note_fret'], ['notes.string', 'notes.fret']),
    )
    parent_id = db.Column(db.Integer, db.ForeignKey('licks.id'), primary_key=True)
    note_string = db.Column(db.Integer, primary_key=True)
    note_fret = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer)
    notes = db.relationship("Note")


class Association(db.Model):
    __tablename__ = 'association'

    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), primary_key=True)
    lick_id = db.Column(db.Integer, db.ForeignKey('licks.id'), primary_key=True)
    licks = db.relationship("Lick")


class Form(db.Model):
    __tablename__ = 'forms'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Integer)
    scale = db.Column(db.Enum(Scale))
    form = db.Column(db.CHAR)
    licks = db.relationship("Association")


class Lick(db.Model):
    __tablename__ = 'licks'

    id = db.Column(db.Integer, primary_key=True)
    notes = db.relationship("NoteSequence")


class Song(db.Model):
    __tablename__ = 'songs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    artist = db.Column(db.String)
    album = db.Column(db.String)
    year = db.Column(db.Integer)
    genre = db.Column(db.String)
    tab = db.Column(db.LargeBinary)


class Note(db.Model):
    __tablename__ = 'notes'

    string = db.Column(db.Integer, primary_key=True)
    fret = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer)
