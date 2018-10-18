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


class FormName(Enum):
    C = 0
    A = 1
    G = 2
    E = 3
    D = 4


class LickNote(db.Model):
    __tablename__ = 'lick_note'
    __table_args__ = (
        db.ForeignKeyConstraint(('note_string', 'note_fret', 'note_value'),
                                ('note.string', 'note.fret', 'note.value')),
    )
    lick_id = db.Column(db.String, db.ForeignKey('lick.id'), primary_key=True)
    note_string = db.Column(db.Integer, primary_key=True)
    note_fret = db.Column(db.Integer, primary_key=True)
    note_value = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer)
    notes = db.relationship("Note")


class FormLick(db.Model):
    __tablename__ = 'form_lick'
    __table_args__ = (
        db.ForeignKeyConstraint(('form_key', 'form_scale', 'form_name'),
                                ('form.key', 'form.scale', 'form.name')),
    )
    form_key = db.Column(db.Integer, primary_key=True)
    form_scale = db.Column(db.Enum(Scale), primary_key=True)
    form_name = db.Column(db.Enum(FormName), primary_key=True)
    lick_id = db.Column(db.String, db.ForeignKey('lick.id'), primary_key=True)
    licks = db.relationship("Lick")


class Form(db.Model):
    __tablename__ = 'form'

    key = db.Column(db.Integer, primary_key=True)
    scale = db.Column(db.Enum(Scale), primary_key=True)
    name = db.Column(db.Enum(FormName), primary_key=True)
    licks = db.relationship("FormLick")


class Lick(db.Model):
    """
    A lick is identified as a sequence of notes. The identifier is a string in this form:
    ssffvvssffvv.....ssffvv, where ss refers to the string (00-12), ff to the fret (00-23) and vv to the value of the
    note (00-11). This sequence is guaranteed to be unique
    """
    __tablename__ = 'lick'

    id = db.Column(db.String, primary_key=True)
    notes = db.relationship("LickNote")


class Song(db.Model):
    __tablename__ = 'song'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    artist = db.Column(db.String)
    album = db.Column(db.String)
    year = db.Column(db.Integer)
    genre = db.Column(db.String)
    tab = db.Column(db.LargeBinary)


class Note(db.Model):
    """
    Value represents the int conversion of the note [0,11]. Marked as primary to identify the possibility of having
    different tunings for the same position on the fretboard
    """
    __tablename__ = 'note'

    string = db.Column(db.Integer, primary_key=True)
    fret = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, primary_key=True)
