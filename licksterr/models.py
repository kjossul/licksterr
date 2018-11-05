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

KEYS = tuple((value, is_major) for is_major in (True, False) for value in range(12))

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
# True for major scales, False for minor scales
SCALES_TYPE = {
    True: [Scale.IONIAN, Scale.LYDIAN, Scale.MIXOLYDIAN, Scale.MAJORPENTATONIC, Scale.MAJORBLUES],
    False: [Scale.DORIAN, Scale.PHRYGIAN, Scale.AEOLIAN, Scale.LOCRIAN, Scale.MINORPENTATONIC, Scale.MINORBLUES]
}
STANDARD_TUNING = [4, 11, 7, 2, 9, 4]
FLOAT_PRECISION = 6


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
    hash = db.Column(db.String(128), unique=True)
    tracks = db.relationship('Track', backref=db.backref("parent"), cascade='all,delete')

    def __str__(self):
        return f"{self.artist} - {self.title}"

    def to_dict(self):
        info = row2dict(self)
        info['tracks'] = [track.id for track in self.tracks]
        return info


class Track(db.Model):
    __tablename__ = 'track'

    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('song.id', ondelete='CASCADE'))
    tuning = db.Column(ARRAY(db.Integer), nullable=False, default=STANDARD_TUNING)
    keys = db.Column(ARRAY(db.Integer))

    measures = association_proxy('track_to_measure', 'measure')
    forms = association_proxy('track_to_form', 'form')

    def __str__(self):
        song = Song.query.get(self.song_id)
        return f"Track #{self.id} for song {song}"

    def add_key(self, key):
        if key in self.keys:
            return
        self.keys.append(key)
        form_matches = defaultdict(float)
        scale_matches = defaultdict(float)
        total_length = 0
        for tm in TrackMeasure.get_measures(self):
            key, is_major = KEYS[key]
            if any(beat.notes for beat in tm.measure.beats):
                total_length += len(tm.indexes)
            for fm in FormMeasure.get_forms(tm.measure):
                form = fm.form
                if form.tuning == self.tuning and form.key == key and form.scale in SCALES_TYPE[is_major]:
                    score = fm.match * len(tm.indexes)
                    form_matches[form] += score
                    scale_matches[form.scale] += score
        top_scale = max(scale_matches, key=scale_matches.get)
        # sets the scale to the pentatonics if there are no differences in match
        if top_scale == Scale.IONIAN and scale_matches[top_scale] == scale_matches[Scale.MAJORPENTATONIC]:
            top_scale = Scale.MAJORPENTATONIC
        elif top_scale == Scale.AEOLIAN and scale_matches[top_scale] == scale_matches[Scale.MINORPENTATONIC]:
            top_scale = Scale.MINORPENTATONIC
        for form, match in form_matches.items():
            if form.scale == top_scale:
                tf = TrackForm(track=self, form=form, match=match)
                db.session.add(tf)

    def remove_key(self, key):
        try:
            self.keys.remove(key)
            key, is_major = key
            for tm in TrackForm.get_forms(self):
                if tm.form.scale in SCALES_TYPE[is_major] and tm.form.key == key:
                    db.session.delete(tm)
            db.session.commit()
        except ValueError:
            pass

    def to_dict(self):
        """
        Returns a description of this track
        :param match: amount of scales to return, in descending order of match
        :return:
        """
        info = row2dict(self)
        info['match'] = []
        for k in self.keys:
            key, is_major = KEYS[k]
            key_result = {'key': notes.int_to_note(key), 'isMajor': is_major, 'forms': defaultdict(float)}
            for tf in TrackForm.get_forms(self):
                if tf.form.key == key:
                    key_result['forms'][tf.form.name] = tf.match
                    key_result['scale'] = tf.form.scale.name
            info['match'].append(key_result)
        return info


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
    measures = association_proxy('form_to_measure', 'measure')
    notes = association_proxy('form_to_note', 'note')

    def __init__(self, note_list, key, scale, name, transpose=False, **kwargs):
        if transpose:
            # Copy-pastes this shape along the fretboard. 11 is excluded because a guitar goes just up the 22th fret
            for string, fret in list(note_list):
                if fret < 11:
                    bisect.insort(note_list, (string, fret + 12))
                elif fret > 11:
                    bisect.insort(note_list, (string, fret - 12))
        note_list = tuple(Note.get(string, fret) for string, fret in note_list)
        super().__init__(key=key, scale=scale, name=name, **kwargs)
        for note in note_list:
            # assigns a different score to each note based on the role it plays in the form
            # todo find better function (currently only assigns 1 to the root and 0.5 to others)
            tuning = kwargs.get('tuning', STANDARD_TUNING)
            score = 1 if (tuning[note.string - 1] + note.fret) % 12 == key else 0.5
            db.session.add(FormNote(form=self, note=note, score=score))

    def __str__(self):
        return f"{self.key} {self.scale} {self.forms}"

    def __hash__(self):
        return self.id

    def to_dict(self):
        return {'name': self.name, 'key': self.key, 'scale': self.scale.name}

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
        strings = (None,) + tuple(String(note) for note in STANDARD_TUNING)
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
    forms = association_proxy('measure_to_form', 'form')
    beats = association_proxy('measure_to_beat', 'beat')

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
                beat_duration = Fraction(1 / beat.duration)
                total_duration += beat_duration
                if beat.notes:
                    containing_forms = set(beat.notes[0].forms)
                    for note in beat.notes[1:]:
                        containing_forms.intersection_update(note.forms)
                    for form in containing_forms:
                        form_match[form] += beat_duration
            for form in form_match:
                form_match[form] /= total_duration
            for form, match in form_match.items():
                db.session.add(FormMeasure(form=form, measure=measure, match=match))
        return measure


class Beat(db.Model):
    __tablename__ = 'beat'

    id = db.Column(db.String(39), primary_key=True)  # 39 max length (6 notes * 6 ('SxFyyP') + 3 ('Dzz')
    duration = db.Column(db.Integer, nullable=False)  # duration of the note(s) (1 - whole, 2 - half, ...)
    notes = association_proxy('beat_to_note', 'note')

    def to_dict(self):
        return {'duration': self.duration, 'notes': [note.to_dict() for note in self.notes]}

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
    forms = association_proxy('note_to_form', 'form')

    def __repr__(self):
        return f"S{self.string}F{self.fret:02}" + ('M' if self.muted else 'P')

    def to_dict(self):
        return row2dict(self)

    @classmethod
    def get(cls, string, fret, muted=False):
        return cls.query.filter_by(string=string, fret=fret, muted=muted).first()


# Associations
class TrackForm(db.Model):
    __tablename__ = 'track_form'
    track_id = db.Column(db.Integer, db.ForeignKey('track.id', ondelete='cascade'), primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id', ondelete='cascade'), primary_key=True)
    # % of this form in the track
    match = db.Column(db.Float(precision=FLOAT_PRECISION))
    # relationships
    track = db.relationship('Track', backref=db.backref('track_to_form', cascade='all, delete-orphan'))
    form = db.relationship('Form', backref=db.backref('form_to_track', cascade='all, delete-orphan'))

    @classmethod
    def get_forms(cls, track):
        return cls.query.filter_by(track=track).all()

    @classmethod
    def get_or_create(cls, track, form):
        tf = cls.query.get((track.id, form.id))
        if not tf:
            instance = cls(track=track, form=form, match=0)
            db.session.add(instance)
            return instance
        return tf


class TrackMeasure(db.Model):
    __tablename__ = 'track_measure'

    track_id = db.Column(db.Integer, db.ForeignKey('track.id', ondelete='cascade'), primary_key=True)
    measure_id = db.Column(db.String(), db.ForeignKey('measure.id', ondelete='cascade'), primary_key=True)
    # % that this measure occupies in the track
    match = db.Column(db.Float(precision=FLOAT_PRECISION))
    indexes = db.Column(db.ARRAY(db.Integer))

    track = db.relationship('Track', backref=db.backref("track_to_measure", cascade='all, delete-orphan'))
    measure = db.relationship('Measure', backref=db.backref("measure_to_track", cascade='all, delete-orphan'))

    def __str__(self):
        return f"Match (track: {self.track}, measure: {self.measure}): {self.match}"

    @classmethod
    def get_measures(cls, track):
        return cls.query.filter_by(track=track).all()


class FormMeasure(db.Model):
    __tablename__ = 'form_measure'

    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), primary_key=True)
    measure_id = db.Column(db.String(), db.ForeignKey('measure.id'), primary_key=True)
    # % of match between this form and this measure
    match = db.Column(db.Float(precision=FLOAT_PRECISION), nullable=False)

    form = db.relationship('Form', backref=db.backref("form_to_measure", cascade='all, delete-orphan'))
    measure = db.relationship('Measure', backref=db.backref("measure_to_form", cascade='all, delete-orphan'))

    def __str__(self):
        return f"Match (form: {self.form}, measure: {self.measure}): {self.match}"

    @classmethod
    def get_forms(cls, measure):
        return cls.query.filter_by(measure=measure).all()

    @classmethod
    def get(cls, form, measure):
        return cls.query.get((form.id, measure.id))


class MeasureBeat(db.Model):
    __tablename__ = 'measure_beat'

    measure_id = db.Column(db.String(), db.ForeignKey('measure.id'), primary_key=True)
    beat_id = db.Column(db.String(39), db.ForeignKey('beat.id'), primary_key=True)
    indexes = db.Column(ARRAY(db.Integer))

    measure = db.relationship('Measure', backref=db.backref('measure_to_beat', cascade='all, delete-orphan'))
    beat = db.relationship('Beat', backref=db.backref('beat_to_measure', cascade='all, delete-orphan'))

    @classmethod
    def get(cls, measure, beat):
        return cls.query.get((measure.id, beat.id))


class FormNote(db.Model):
    __tablename__ = 'form_note'

    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), primary_key=True)
    score = db.Column(db.Integer)
    # relationships
    form = db.relationship('Form', backref=db.backref('form_to_note', cascade='all, delete-orphan'))
    note = db.relationship('Note', backref=db.backref('note_to_form', cascade='all, delete-orphan'))


class BeatNote(db.Model):
    __tablename__ = 'beat_note'

    beat_id = db.Column(db.String(39), db.ForeignKey('beat.id'), primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), primary_key=True)
    # todo store not effect here
    # relationships
    beat = db.relationship('Beat', backref=db.backref('beat_to_note', cascade='all, delete-orphan'))
    note = db.relationship('Note', backref=db.backref('note_to_beat', cascade='all, delete-orphan'))
