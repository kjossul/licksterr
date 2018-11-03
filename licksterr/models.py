import bisect
import logging
from collections import defaultdict
from enum import Enum
from fractions import Fraction

from flask_sqlalchemy import SQLAlchemy
from mingus.core import notes, scales
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.associationproxy import association_proxy

from licksterr.util import row2dict

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


NOTES_DICT = {notes.int_to_note(value, accidental): value for value in range(12) for accidental in ('#', 'b')}

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

STANDARD_TUNING = [4, 9, 2, 7, 11, 4]


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


class Song(db.Model):
    __tablename__ = 'song'

    id = db.Column(db.Integer, primary_key=True)
    album = db.Column(db.String())
    artist = db.Column(db.String())
    title = db.Column(db.String())
    tempo = db.Column(db.Integer)
    year = db.Column(db.Integer)
    tracks = db.relationship('Track')

    def __str__(self):
        return f"{self.artist} - {self.title}"

    def to_dict(self):
        info = row2dict(self)
        info['tracks'] = [track.id for track in self.tracks]
        return info


class Track(db.Model):
    __tablename__ = 'track'

    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
    tuning = db.Column(ARRAY(db.Integer), nullable=False, default=STANDARD_TUNING)
    measures = association_proxy('track_measure', 'measure')
    notes = association_proxy('track_note', 'note')

    def __str__(self):
        song = Song.query.get(self.song_id)
        return f"Track #{self.id} for song {song}"

    def get_notes_by_hit(self):
        return sorted(self.notes,
                      key=lambda note: TrackNote.query.get((self.id, note.id)).match, reverse=True)

    def to_dict(self):
        info = row2dict(self)

class Form(db.Model):
    __tablename__ = 'form'
    __table_args__ = (
        db.UniqueConstraint('key', 'scale', 'name', 'tuning'),
    )
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Integer, nullable=False)
    scale = db.Column(db.Enum(Scale), nullable=False)
    name = db.Column(db.String(), nullable=False)
    tuning = db.Column(ARRAY(db.Integer), nullable=False, default=STANDARD_TUNING)
    measures = association_proxy('form_measure', 'measure')
    notes = association_proxy('form_note', 'note')

    def __init__(self, notes, key, scale, name, transpose=False, **kwargs):
        if transpose:
            # Copy-pastes this shape along the fretboard. 11 is escluded because a guitar goes just up the 22th fret
            note_list = list(notes)
            for string, fret in note_list:
                if fret < 11:
                    bisect.insort(notes, (string, fret + 12))
                elif fret > 11:
                    bisect.insort(notes, (string, fret - 12))
        notes = tuple(Note.get(string, fret) for string, fret in notes)
        super().__init__(key=key, scale=scale, name=name, **kwargs)
        for note in notes:
            db.session.add(FormNote(form=self, note=note))

    def __str__(self):
        return f"{self.key} {self.scale} {self.forms}"

    @classmethod
    def get(cls, key, scale, name):
        return cls.query.filter_by(key=key, scale=scale, name=name).first()

    @classmethod
    def calculate_caged_form(cls, key, scale, form, form_start=0, transpose=False):
        """
        Calculates the notes belonging to this shape. This is done as follows:
        Find the notes on the 6th string belonging to the scale, and pick the first one that is on a fret >= form_start.
        Then progressively build the scale, go to the next string if the distance between the start and the note is
        greater than 3 frets (the pinkie would have to stretch and it's easier to get that note going down a string).
        If by the end not all the roots are included in the form, call the function again and start on an higher fret.
        """
        strings = (None,) + tuple(String(note) for note in STANDARD_TUNING[::-1])
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


class Measure(db.Model):
    __tablename__ = 'measure'

    id = db.Column(db.String(), primary_key=True)
    beats = association_proxy('measure_beat', 'beat')

    @classmethod
    def get_or_create(cls, beats, tuning=None):
        """
        Retrieves the measure with the given beats or creates a new one from them. Upon creation, known forms in the
        database are matched against the notes found in each beat and % of matching is calculated.
        """
        tuning = tuning if tuning else STANDARD_TUNING
        id = ''.join(beat.id for beat in beats)
        measure = Measure.query.get(id)
        if not measure:
            measure = Measure(id=id)
            form_match = defaultdict(float)  # % of duration a form occupies in this measure
            total_duration = 0
            for i, beat in enumerate(beats):
                mb = MeasureBeat.get(measure, beat)
                if not mb:
                    db.session.add(MeasureBeat(measure=measure, beat=beat, indexes=[i]))
                else:
                    mb.indexes.append(i)
                total_duration += Fraction(1 / beat.duration)
                if beat.notes:
                    containing_forms = {form for form in beat.notes[0].forms if form.tuning == tuning}
                    for note in beat.notes[1:]:
                        matching_forms = {form for form in note.forms if form.tuning == tuning}
                        containing_forms.intersection_update(matching_forms)
                    form_match.update({form: form_match[form] + Fraction(1 / beat.duration)
                                       for form in containing_forms})
            form_match.update({k: form_match[k] / total_duration for k in form_match.keys()})
            for form, match in form_match.items():
                db.session.add(FormMeasure(form=form, measure=measure, match=match))
        return measure


class Beat(db.Model):
    __tablename__ = 'beat'

    id = db.Column(db.String(39), primary_key=True)  # 39 max length (6 notes * 6 ('SxFyyP') + 3 ('Dzz')
    duration = db.Column(db.Integer, nullable=False)  # duration of the note(s) (1 - whole, 2 - half, ...)
    notes = association_proxy('beat_note', 'note')

    @classmethod
    def get_or_create(cls, beat):
        if len(beat.notes) > 6:
            raise ValueError("Can't have more than two notes per string!")
        notes = tuple(Note.get(note.string, note.value)
                      for note in sorted(beat.notes, key=lambda note: (note.string, note.value)))
        id = ''.join(repr(note) for note in notes) + f'D{beat.duration.value:02}'
        b = Beat.query.get(id)
        if not b:
            b = Beat(id=id, duration=beat.duration.value)
            db.session.add(b)
            for note in notes:
                db.session.add(BeatNote(beat=b, note=note))
        return b


class Note(db.Model):
    __tablename__ = 'note'
    __table_args__ = (
        db.UniqueConstraint('string', 'fret', 'muted'),
    )

    id = db.Column(db.Integer, primary_key=True)
    string = db.Column(db.Integer, nullable=False)
    fret = db.Column(db.Integer, nullable=False)
    muted = db.Column(db.Boolean, nullable=False, default=False)
    forms = association_proxy('form_note', 'form')

    def __repr__(self):
        return f"S{self.string}F{self.fret:02}" + ('M' if self.muted else 'P')

    @classmethod
    def get(cls, string, fret, muted=False):
        return cls.query.filter_by(string=string, fret=fret, muted=muted).first()


# Associations

class TrackMeasure(db.Model):
    __tablename__ = 'track_measure'

    track_id = db.Column(db.Integer, db.ForeignKey('track.id'), primary_key=True)
    measure_id = db.Column(db.String(), db.ForeignKey('measure.id'), primary_key=True)
    # % that this measure occupies in the track
    match = db.Column(db.Float)
    indexes = db.Column(db.ARRAY(db.Integer))

    track = db.relationship('Track', backref=db.backref("track_measure", cascade='all, delete-orphan'))
    measure = db.relationship('Measure')

    def __str__(self):
        return f"Match (track: {self.track}, measure: {self.measure}): {self.match}"

    @classmethod
    def get_top(cls, track):
        return sorted(cls.query.filter_by(track=track).all(), key=lambda x: x.match, reverse=True)


class FormMeasure(db.Model):
    __tablename__ = 'form_measure'

    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), primary_key=True)
    measure_id = db.Column(db.String(), db.ForeignKey('measure.id'), primary_key=True)
    # % of match between this form and this measure
    match = db.Column(db.Float, nullable=False)

    form = db.relationship('Form', backref=db.backref("form_measure", cascade='all, delete-orphan'))
    measure = db.relationship('Measure')

    def __str__(self):
        return f"Match (form: {self.form}, measure: {self.measure}): {self.match}"

    @classmethod
    def get_top(cls, measure):
        return sorted(cls.query.filter_by(track=measure).all(), key=lambda x: x.match, reverse=True)

    @classmethod
    def get(cls, form, measure):
        return cls.query.get((form.id, measure.id))


class MeasureBeat(db.Model):
    __tablename__ = 'measure_beat'

    measure_id = db.Column(db.String(), db.ForeignKey('measure.id'), primary_key=True)
    beat_id = db.Column(db.String(39), db.ForeignKey('beat.id'), primary_key=True)
    indexes = db.Column(ARRAY(db.Integer))

    measure = db.relationship('Measure', backref=db.backref('measure_beat', cascade='all, delete-orphan'))
    beat = db.relationship('Beat')

    @classmethod
    def get(cls, measure, beat):
        return cls.query.get((measure.id, beat.id))


class TrackNote(db.Model):
    __tablename__ = 'track_note'

    track_id = db.Column(db.Integer, db.ForeignKey('track.id'), primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), primary_key=True)
    match = db.Column(db.Float)
    # relationships
    track = db.relationship('Track', backref=db.backref('track_note', cascade='all, delete-orphan'))
    note = db.relationship('Note')

    @classmethod
    def get_match(cls, track, note):
        return cls.query.get((track.id, note.id)).match


class FormNote(db.Model):
    __tablename__ = 'form_note'

    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), primary_key=True)
    # relationships
    form = db.relationship('Form', backref=db.backref('form_note', cascade='all, delete-orphan'))
    note = db.relationship('Note', backref=db.backref('form_note', cascade='all, delete-orphan'))


class BeatNote(db.Model):
    __tablename__ = 'beat_note'

    beat_id = db.Column(db.String(39), db.ForeignKey('beat.id'), primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), primary_key=True)
    # todo store not effect here
    # relationships
    beat = db.relationship('Beat', backref=db.backref('beat_note', cascade='all, delete-orphan'))
    note = db.relationship('Note')
