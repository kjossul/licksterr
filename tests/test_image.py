import os
import unittest

from PIL import ImageColor

from src import ASSETS_FOLDER
from src.image import GuitarImage


class TestImage(unittest.TestCase):
    TEST_ASSETS = os.path.join(ASSETS_FOLDER, "tests")

    def test_fill(self):
        """Should produce an image with all circles filled in the standard color and E notes in red"""
        guitar = GuitarImage()
        for string in guitar.strings.values():
            for fret, note in enumerate(string.notes):
                color = 'red' if note == 'E' else 'green'
                im = guitar.fill_circle(string.positions[fret], color=ImageColor.getcolor(color, mode='RGBA'))
        im.save(os.path.join(self.TEST_ASSETS, "test_fill.png"))
