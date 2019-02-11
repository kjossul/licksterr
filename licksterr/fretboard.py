import logging

from flask import current_app
from fretboard import Fretboard
from mingus.core import keys, notes

from licksterr.models import SCALES_DICT, Form, db, Note, FormNote, ENUM_DICT

logger = logging.getLogger(__name__)


def create_notes_and_forms():
    logger.debug("Adding notes to database")
    db.session.add(Note(string=0, fret=0))  # "Pause" note
    for string in range(1, 7):
        for fret in range(0, 30):
            db.session.add(Note(string=string, fret=fret))
    db.session.commit()
    logger.debug("Generating forms..")
    for key, scale in yield_scales():
        logger.debug(f"Generating {key} {scale}")
        for form_name in 'CAGED':
            form = Form.calculate_caged_form(key, scale, form_name, transpose=True)
            db.session.add(form)
            draw_fretboard(form)
    db.session.commit()
    logger.info("Database initialization completed.")


def yield_scales(scales_list=SCALES_DICT.keys(), keys_list=None):
    for scale in scales_list:
        current_keys = keys_list
        if not current_keys:
            current_keys = keys.minor_keys if scale.type == 'minor' else keys.major_keys
        for key in current_keys[2:-1]:
            yield key, scale


def draw_fretboard(form):
    style = {"drawing": {"font_size": 12}}
    # fixme correct key names for minor-major scales
    scale = ENUM_DICT[form.scale](form.key_name)
    scale_notes = scale.ascending()
    fns = list(FormNote.query.filter_by(form=form))
    start = min(fn.note.fret for fn in fns)
    drawable = [fn for fn in fns if start <= fn.note.fret < start + 5]
    # If this shape is "cut" near the neck show the full shape higher up the fretboard
    if len(drawable) < len(fns) / 2:
        drawable = [fn for fn in fns if fn not in drawable]
        start = min(fn.note.fret for fn in drawable)
    shape = Fretboard(frets=(start, start + 4), style=style)
    for fn in drawable:
        if start <= fn.note.fret < start + 5:
            note_value = (form.key + fn.degree) % 12
            note_name = next(note for note in scale_notes if notes.note_to_int(note) == note_value)
            color = 'chocolate' if fn.degree == 0 else 'dodgerblue'
            shape.add_marker(abs(fn.note.string - 6), fn.note.fret, label=note_name, color=color)
    filename = current_app.config["SHAPES_DIR"] / f"{form.id}.svg"
    shape.save(filename)
