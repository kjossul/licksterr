import os

from mingus.core import scales, keys

from src import ASSETS_FOLDER
from src.guitar import Form, Lick, Chord
from src.image import GuitarImage

ANALYSIS_FOLDER = os.path.join(ASSETS_FOLDER, "analysis")


class Analyzer:
    def __init__(self, guitar):
        self.guitar = guitar
        self.licks = [Lick()]
        self.chords = []
        self.scales_dict = {}
        for key in keys.major_keys:
            for scale in Form.SUPPORTED_SCALES:
                self.scales_dict[key] = {scale: self.guitar.get_notes(scale(key).ascending())}

    def parse_track(self):
        start, end = 1, None
        for i, measure in enumerate(self.guitar.measures):
            for beat in measure.beats:
                if beat.chord:
                    end = i
                    self.licks[-1].start = start
                    self.licks[-1].end = end
                    start = i
                    self.licks.append(Lick())
                    self.chords.append(Chord(beat.chord))
                elif beat.notes:
                    for note in beat.notes:
                        self.licks[-1].notes.append(note)
                else:  # todo consider a pause after some time (at least one measure?) has passed without notes
                    pass
        self.licks[-1].start = start
        self.licks[-1].end = i

    def find_used_scales(self):
        pass


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
        for form in Form.ROOT_FORMS:
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
