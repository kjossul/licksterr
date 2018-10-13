import os
import unittest

from src import ASSETS_FOLDER
from src.guitar import Song


class TestParser(unittest.TestCase):
    TEST_ASSETS = os.path.join(ASSETS_FOLDER, "tests")

    @classmethod
    def setUpClass(cls):
        cls.song = Song(os.path.join(cls.TEST_ASSETS, "test.gp5"))

    def test_bpm(self):
        self.assertEqual(120, self.song.tempo)

    def test_tuning(self):
        self.assertEqual("EADGBE", self.song.guitars[0].tuning)

    def test_notes(self):
        beat = self.song.guitars[0].measures[0].beats[0]
        # all strings are strummed on zero exactly once
        self.assertTrue(all(note.value == 0 for note in beat.notes))

    def test_chords(self):
        chord = self.song.guitars[1].measures[0].beats[0].chord
        self.assertEqual('C', chord.name)