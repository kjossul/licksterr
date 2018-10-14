import os
import unittest
from collections import defaultdict

from mingus.core import scales
from mingus.core.keys import major_keys

from src import ASSETS_FOLDER
from src.guitar import Song, Form


class TestGuitar(unittest.TestCase):
    TEST_ASSETS = os.path.join(ASSETS_FOLDER, "tests")

    @classmethod
    def setUpClass(cls):
        cls.song = Song(os.path.join(cls.TEST_ASSETS, "test.gp5"))

    def test_data(self):
        data = {
            "album": 'album',
            "artist": 'artist',
            "year": '2018',
            "genre": 'Moderate',
            "title": 'name'
        }
        self.assertDictEqual(data, self.song.data)

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

    def test_intervals(self):
        intervals = self.song.guitars[2].calculate_intervals()
        expected = {'2': 1, '3': 1, 'b3': 2, 'b7': 1}
        self.assertDictEqual(expected, intervals)

    def test_caged(self):
        """CAGED system should find all roots"""
        for key in major_keys:
            expected = self.song.guitars[0].get_notes(key)
            actual = defaultdict(set)
            for f in 'CAGED':
                for string, note in Form.get_form_roots(key, f).items():
                    actual[string].add(note)
                    if note < 11:
                        actual[string].add(note + 12)
            self.assertDictEqual(expected, actual)

    def test_form(self):
        scale = scales.MinorPentatonic
        key = 'A'
        for f in 'CAGED':
            form = Form(key, scale, f)
            for string, notes in form.notes.items():
                self.assertEqual(2, len(notes))
