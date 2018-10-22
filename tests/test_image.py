import os

from PIL import ImageColor

from licksterr.image import GuitarImage
from tests import TEST_ASSETS, LicksterrTest


class TestImage(LicksterrTest):
    FORMS = 'CAGED'

    @classmethod
    def setUpClass(cls):
        cls.guitar = GuitarImage()

    def test_fill(self):
        """Should produce an image with all circles filled in the standard color and E notes in red"""
        im = self.guitar.im.copy()
        for string in self.guitar.strings[1:]:
            for fret, note in string:
                color = 'red' if note == 'E' else 'green'
                self.guitar.fill_note(string, fret, ImageColor.getcolor(color, mode='RGBA'), im=im)
        im.save(os.path.join(TEST_ASSETS, "test_fill.png"))
