import logging

from mingus.core import keys

from licksterr.models import SCALES_DICT, Form, db, Note

logger = logging.getLogger(__name__)


def init_db():
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
    db.session.commit()
    logger.info("Database initialization completed.")


def yield_scales(scales_list=SCALES_DICT.keys(), keys_list=None):
    for scale in scales_list:
        current_keys = keys_list
        if not current_keys:
            current_keys = keys.minor_keys if scale.type == 'minor' else keys.major_keys
        for key in current_keys[2:-1]:
            yield key, scale
