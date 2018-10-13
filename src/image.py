import os

from PIL import Image, ImageColor

from src import ASSETS_FOLDER


class Fretboard:
    def __init__(self):
        self.im = Image.open(os.path.join(ASSETS_FOLDER, "blank_fret_board.png"))
        # todo add open strings
        # The F note on the high E is at (46,15). H step: 27px. V step: 16px. 22 frets total.
        self.strings = {i + 1: {j + 1: (46 + j * 27, 15 + i * 16) for j in range(22)} for i in range(6)}

    def fill_circle(self, xy, color=ImageColor.getrgb('#00ff00ff'), im=None):
        """Fills the area around the dot until it founds the borders"""
        im = im if im else self.im
        pixel = im.getpixel(xy)
        if pixel not in (ImageColor.getrgb('#000000ff'), color):  # skips if black or alraedy filled
            im.putpixel(xy, color)
            for ij in (1, 0), (0, 1), (-1, 0), (0, -1):
                new_xy = (xy[0]+ij[0], xy[1]+ij[1])
                self.fill_circle(new_xy, color, im)
        return im


def main():
    f = Fretboard()
    im = f.fill_circle(f.strings[1][1])
    im.save(os.path.join(ASSETS_FOLDER, "test.png"))


if __name__ == '__main__':
    main()
