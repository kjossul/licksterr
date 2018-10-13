import os

from mingus.core import scales
from mingus.core.keys import minor_keys, major_keys

from src import ASSETS_FOLDER
from src.guitar import Form
from src.image import GuitarImage

ANALYSIS_FOLDER = os.path.join(ASSETS_FOLDER, "analysis")


def yield_scales():
    for scale in scales._Scale.__subclasses__():
        if scale.type == 'diatonic':
            continue
        for key in (minor_keys if scale.type == 'minor' else major_keys):
            yield (key, scale)


def create_scales():
    guitar = GuitarImage()
    for key, scale in yield_scales():
        for form in Form.FORMS:
            im = guitar.fill_scale_position(key, scale, form, im=guitar.im.copy())
            if key.islower():
                key = key[0].upper() + key[1:]
            dir = os.path.join(ANALYSIS_FOLDER, "scales", scale.__name__, key)
            if not os.path.exists(dir):
                os.makedirs(dir)
            im.save(os.path.join(dir, f"{form}.png"))
