import os

from mingus.core import scales

from src import ASSETS_FOLDER
from src.guitar import Form
from src.image import GuitarImage

ANALYSIS_FOLDER = os.path.join(ASSETS_FOLDER, "analysis")


def yield_scales(keys=('G',)):
    for scale in scales._Scale.__subclasses__():
        if scale.type == 'diatonic':
            continue
        for key in keys:
            yield (key, scale)


def create_scales():
    guitar = GuitarImage()
    for key, scale in yield_scales():
        for form in Form.FORMS:
            im = guitar.fill_scale_position(key, scale, form, im=guitar.im.copy())
            if key.islower():
                key = key[0].upper() + key[1:]
            dir = os.path.join(ANALYSIS_FOLDER, "scales", scale.__name__)
            if not os.path.exists(dir):
                os.makedirs(dir)
            im.save(os.path.join(dir, f"{form}.png"))


if __name__ == '__main__':
    create_scales()