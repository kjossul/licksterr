import os

from mingus.core import scales

from src import ASSETS_FOLDER
from src.guitar import Form
from src.image import GuitarImage

ANALYSIS_FOLDER = os.path.join(ASSETS_FOLDER, "analysis")


def yield_scales(keys=('G',)):
    not_supported = ('Diatonic', 'WholeTone')
    for scale in scales._Scale.__subclasses__():
        if any(x == scale.__name__ for x in not_supported):
            continue
        for key in keys:
            yield (key, scale)


def create_scales():
    guitar = GuitarImage()
    for key, scale in yield_scales():
        for form in Form.FORMS:
            try:
                im = guitar.fill_scale_position(key, scale, form, im=guitar.im.copy())
                if key.islower():
                    key = key[0].upper() + key[1:]
                dir = os.path.join(ANALYSIS_FOLDER, "scales", scale.__name__)
                if not os.path.exists(dir):
                    os.makedirs(dir)
                im.save(os.path.join(dir, f"{form}.png"))
            except NotImplementedError:
                pass


if __name__ == '__main__':
    create_scales()