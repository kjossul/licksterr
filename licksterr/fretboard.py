import logging

from licksterr.models import SCALES_DICT, db, Note, Tuning, STANDARD_TUNING, Scale

logger = logging.getLogger(__name__)


def init_fretboard_elements():
    db.session.add(Note(string=-1, fret=0))  # "Pause" note
    for string in range(0, 6):
        for fret in range(-1, 30):  # -1 encodes the muted note
            db.session.add(Note(string=string, fret=fret))
    logger.debug("Added notes to database.")
    standard_tuning = Tuning(name="Standard", value=STANDARD_TUNING)
    db.session.add(standard_tuning)
    db.session.commit()
    logger.debug("Added standard tuning to database.")
    for scale in SCALES_DICT.keys():
        db.session.add(Scale(scale, standard_tuning))
    logger.debug("Added scales to database.")
    db.session.commit()
    logger.info("Database initialization completed.")
