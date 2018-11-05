import os

from PIL import Image, ImageColor

from licksterr import ASSETS_DIR
from licksterr.models import String, Form, STANDARD_TUNING
from licksterr.util import timing


class GuitarImage:
    def __init__(self, tuning=STANDARD_TUNING):
        self.strings = (None,) + tuple(String(note) for note in tuning[::-1])
        self.im = Image.open(os.path.join(ASSETS_DIR, "blank_fret_board.png"))
        # The open high E string circle is at (19,15). H step: 27px. V step: 16px. 22 frets total + open strings
        for i, string in enumerate(self.strings[1:]):
            string.positions = tuple((19 + j * 27, 15 + i * 16) for j in range(23))

    def fill_scale_position(self, key, scale, form, im=None):
        # todo make color pattern for scale degrees customizable
        im = im if im else self.im
        form = Form.get(key, scale, form)
        for note in form.notes:
            color = 'red' if note.fret in self.strings[note.string][form.key] else 'green'
            self.fill_note(self.strings[note.string], note.fret, color=ImageColor.getcolor(color, 'RGBA'), im=im)
        return im

    @timing
    def draw_note_heatmap(self, track, im=None):
        colors = {
            0: 'blue',
            0.05: 'cyan',
            0.10: 'yellow',
            0.15: 'orange',
            0.2: 'red'
        }
        im = im if im else self.im
        for note in track.notes:
            match = TrackNote.get_match(track, note)
            k = min((k for k in colors), key=lambda k: abs(k - match))
            color = ImageColor.getcolor(colors[k], mode='RGBA')
            self.fill_note(self.strings[note.string], note.fret, color=color, im=im)
        return im

    def fill_note(self, string, fret, color=None, im=None):
        self.fill_circle(string.positions[fret], color=color, im=im)

    def fill_circle(self, xy, color=None, im=None):
        """Fills the area around the dot until it founds the borders"""
        color = color if color else ImageColor.getcolor('green', mode='RGBA')
        black = ImageColor.getcolor('black', mode='RGBA')
        im = im if im else self.im
        pixel = im.getpixel(xy)
        if pixel not in (black, color):  # skips if black or already filled
            im.putpixel(xy, color)
            for ij in (1, 0), (0, 1), (-1, 0), (0, -1):  # goes to adjacent pixels
                new_xy = (xy[0] + ij[0], xy[1] + ij[1])
                self.fill_circle(new_xy, color, im)
        return im


def main():
    pass


if __name__ == '__main__':
    main()
