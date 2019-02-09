import logging
from collections import OrderedDict

from mingus.core import keys

from licksterr.models import SCALES_DICT, Form, db, Note, TrackMeasure, MeasureBeat, FormNote, \
    BeatNote

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


def get_track_interval_list(track, include_rests=True, include_ties=True):
    notes_dict = get_track_notes_degree_dict(track)
    measure_dict = {}  # measure : beat_list
    for tm in TrackMeasure.query.filter_by(track_id=track.id):
        beat_dict = {}  # beat : interval list
        for mb in MeasureBeat.query.filter_by(measure_id=tm.measure_id):
            degrees = []
            for bn in BeatNote.query.filter_by(beat_id=mb.beat_id):
                try:
                    if (include_rests or bn.note.string != 0) and (include_ties or not bn.tie):
                        degrees.append([notes_dict[bn.note_id]])
                except KeyError:
                    logger.debug(f"No scale degree recognized at beat #{mb.indexes}")
                    degrees.append([])
            for i in mb.indexes:
                beat_dict[i] = degrees
        for i in tm.indexes:
            measure_dict[i] = OrderedDict(sorted(beat_dict.items()))
    # Flattens ordered dictionary into a single list of intervals
    return [degree for m, bd in sorted(measure_dict.items()) for b, dl in bd.items() for degree in dl]


def get_track_notes_degree_dict(track):
    out = {}  # Note : relative degree
    track_match = track.get_form_match()
    for result in track_match:
        for form_id in result["forms"]:
            for fn in FormNote.query.filter_by(form_id=form_id):
                out[fn.note_id] = fn.degree
    return out
