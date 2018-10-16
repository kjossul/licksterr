import os

from PIL import Image, ImageColor

from src import ASSETS_FOLDER
from src.guitar import Guitar, Form


class GuitarImage(Guitar):
    def __init__(self, track=None, tuning='EADGBE'):
        super().__init__(track=track, tuning=tuning)
        self.im = Image.open(os.path.join(ASSETS_FOLDER, "blank_fret_board.png"))
        # The open high E string circle is at (19,15). H step: 27px. V step: 16px. 22 frets total + open strings
        for string in self.strings:
            string.positions = tuple((19 + note.fret * 27, 15 + (string.index - 1) * 16) for note in string.notes)

    def fill_scale_position(self, key, scale, form, im=None):
        # todo make color pattern for scale degrees customizable
        im = im if im else self.im
        form = Form(key, scale, form)
        for note in form.notes:
            color = 'red' if note in form.roots else 'green'
            self.fill_note(note, color=ImageColor.getcolor(color, 'RGBA'), im=im)
        return im

    def fill_note(self, note, color=None, im=None):
        string = self.strings[note.string - 1]
        self.fill_circle(string.positions[note.fret], color=color, im=im)

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


class FormImage(Form):
    pass  # todo implement subclassing of Form class


def main():
    pass


if __name__ == '__main__':
    main()
