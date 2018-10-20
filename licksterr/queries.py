import logging
from itertools import combinations, chain

from mingus.core import keys

from licksterr.models import SCALES_DICT, Form, db

logger = logging.getLogger(__name__)


def init_forms():
    for key, scale in yield_scales():
        current_forms = {}
        for form_name in 'CAGED':
            current_forms[form_name] = Form.calculate_caged_form(key, scale, form_name, transpose=True)
            db.session.add(current_forms[form_name])
        # Stores also all the possible combinations of each form
        for combo in chain.from_iterable(combinations('CAGED', i) for i in range(2, 6)):
            combo_form = Form.join_forms(current_forms[form] for form in combo)
            db.session.add(combo_form)
    db.session.commit()
    logger.info("Generated CAGED forms for standard tuning.")


def yield_scales(scales_list=SCALES_DICT.keys(), keys_list=None):
    for scale in scales_list:
        current_keys = keys_list
        if not current_keys:
            current_keys = keys.minor_keys if scale.type == 'minor' else keys.major_keys
        for key in current_keys[2:-1]:
            yield key, scale
