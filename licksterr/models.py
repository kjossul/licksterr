import bisect
import logging
from enum import Enum

from flask_sqlalchemy import SQLAlchemy
from mingus.core import notes, scales
from sqlalchemy.dialects.postgresql import ARRAY

from licksterr.guitar import String

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
    MINORPENTATONIC = 7
    MAJORPENTATONIC = 8
    MINORBLUES = 9
    MAJORBLUES = 10


SCALES_DICT = {
    scales.Ionian: Scale.IONIAN,
    scales.Dorian: Scale.DORIAN,
    scales.Phrygian: Scale.PHRYGIAN,
    scales.Lydian: Scale.LYDIAN,
    scales.Mixolydian: Scale.MIXOLYDIAN,
    scales.Aeolian: Scale.AEOLIAN,
    scales.Locrian: Scale.LOCRIAN,
    scales.MinorPentatonic: Scale.MINORPENTATONIC,
    scales.MajorPentatonic: Scale.MAJORPENTATONIC,
    scales.MinorBlues: Scale.MINORBLUES,
    scales.MajorBlues: Scale.MAJORBLUES
}


class NoteContainer(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    notes = db.Column(ARRAY(db.Integer, dimensions=2), nullable=False)
    tuning = db.Column(ARRAY(db.Integer), nullable=False)

    def __init__(self, tuning=(4, 9, 2, 7, 11, 4), **kwargs):
        super().__init__(tuning=tuning, **kwargs)

    @classmethod
    def contains_note(cls, string, fret):
        return cls.notes.contains([[string, fret]])


class Lick(NoteContainer):
    __tablename__ = 'lick'

    unique_key = db.Column(db.String, nullable=False, unique=True)
    # starting and ending measures
    start = db.Column(db.Integer)
    end = db.Column(db.Integer)
    forms = db.relationship("Form", secondary=lambda: form_lick)

    def __init__(self, notes, **kwargs):
        kwargs['unique_key'] = ''.join(f"S{string}F{fret:02}" for string, fret in notes)
        super().__init__(notes=notes, **kwargs)


class Form(NoteContainer):
    __tablename__ = 'form'
    __table_args__ = (
        db.UniqueConstraint('key', 'scale', 'name', 'tuning'),
    )

    key = db.Column(db.Integer, nullable=False)
    scale = db.Column(db.Enum(Scale), nullable=False)
    name = db.Column(db.String, nullable=False)
    licks = db.relationship("Lick", secondary=lambda: form_lick)

    def __init__(self, notes, key, scale, name, transpose=False, **kwargs):
        if transpose:
            # Copy-pastes this shape along the fretboard. 11 is escluded because a guitar goes just up the 22th fret
            note_list = list(notes)
            for string, fret in note_list:
                if fret < 11:
                    bisect.insort(notes, (string, fret + 12))
                elif fret > 11:
                    bisect.insort(notes, (string, fret - 12))
        super().__init__(notes=notes, key=key, scale=scale, name=name, **kwargs)

    def __str__(self):
        return f"{self.key} {self.scale} {self.forms}"

    @classmethod
    def join_forms(cls, forms):
        keys, scales, tunings, name = set(), set(), set(), ''
        for form in forms:
            keys.add(form.key)
            scales.add(form.scale)
            tunings.add(form.tuning)
            name += form.name
        # Can't combine forms of different keys / scales / tunings
        assert len(keys) == len(scales) == len(tunings) == 1
        notes = tuple(sorted({note for form in forms for note in form.notes}))
        return cls(notes, keys.pop(), scales.pop(), name, tuning=tunings.pop())

    @classmethod
    def calculate_caged_form(cls, key, scale, form, form_start=0, transpose=False):
        """
        Calculates the notes belonging to this shape. This is done as follows:
        Find the notes on the 6th string belonging to the scale, and pick the first one that is on a fret >= form_start.
        Then progressively build the scale, go to the next string if the distance between the start and the note is
        greater than 3 frets (the pinkie would have to stretch and it's easier to get that note going down a string).
        If by the end not all the roots are included in the form, call the function again and start on an higher fret.
        """
        strings = (None,) + tuple(String(note) for note in 'EADGBE'[::-1])
        # Indexes of string for each root form
        root_forms = {
            'C': (2, 5),
            'A': (5, 3),
            'G': (3, 1, 6),
            'E': (1, 6, 4),
            'D': (4, 2),
        }
        l_string = root_forms[form][0]  # string that has the leftmost root
        r_strings = root_forms[form][1:]  # other strings
        notes_list = []
        roots = [next((l_string, fret) for fret in strings[l_string][key] if fret >= form_start)]
        roots.extend(next((string, fret) for fret in strings[string][key] if fret >= roots[0][1])
                     for string in r_strings)
        scale_notes = scale(key).ascending()
        candidates = strings[6].get_notes(scale_notes)
        # picks the first note that is inside the form
        notes_list.append(next((6, fret) for fret in candidates if fret >= form_start))
        start = notes_list[0][1]
        for i in range(6, 0, -1):
            string = strings[i]
            if i == 1:
                # Removes the note added on the high E and just copy-pastes the low E
                notes_list.pop()
                # Copies the remaining part of the low E in the high E
                for note, fret in ((s, fret) for s, fret in notes_list.copy() if s == 6):
                    notes_list.append((1, fret))
                break
            for fret in string.get_notes(scale_notes):
                if fret <= start:
                    continue
                # picks the note on the higher string that is closer to the current position of the index finger
                higher_string_fret = min(strings[i - 1].get_notes([string.notes[fret]]),
                                         key=lambda x: abs(start - x))
                # No note is present in a feasible position on the higher string.
                if higher_string_fret > fret:
                    return cls.calculate_caged_form(key, scale, form, form_start=form_start + 1, transpose=transpose)
                # A note is too far if the pinkie has to go more than 3 frets away from the index finger
                if fret - start > 3:
                    notes_list.append((i - 1, higher_string_fret))
                    start = higher_string_fret
                    break
                else:
                    notes_list.append((i, fret))
        if not set(roots).issubset(set(notes_list)):
            return cls.calculate_caged_form(key, scale, form, form_start=form_start + 1, transpose=transpose)
        key = notes.note_to_int(key)
        scale = getattr(Scale, scale.__name__.upper())
        return cls(notes_list, key, scale, form, transpose=transpose)


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
