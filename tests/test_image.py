import os
import unittest

from src import ASSETS_FOLDER
from src.image import Fretboard


class TestGuitar(unittest.TestCase):
    TEST_ASSETS = os.path.join(ASSETS_FOLDER, "tests")

    def test_fill(self):
        """Should produce an image with all circles filled in the standard color"""
        f = Fretboard()
        for string in range(1, 7):
            for fret in range(0, 23):
                im = f.fill_circle(f.strings[string][fret])
        im.save(os.path.join(self.TEST_ASSETS, "test_fill.png"))
