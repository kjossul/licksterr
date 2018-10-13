import os
import unittest

from mingus.core.keys import major_keys

from src import ASSETS_FOLDER
from src.analyzer import yield_scales
from src.guitar import Song, Form, String


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
            actual = set()
            for f in 'CAGED':
                for form in Form.get_root_forms(key, f):
                    for note in form:
                        if note[1] < String.FRETS:
                            actual.add(note)
            self.assertSetEqual(expected, actual)

    def test_scale(self):
        """Combining the boxes should yield the same result as getting all the notes"""
        for key, scale in yield_scales():
            forms = [Form(key, scale, form, octave) for form in Form.FORMS.keys() for octave in (0, 1)]
            actual = set().union(*[form.notes for form in forms])
            expected = self.song.guitars[0].get_notes(scale(key).ascending())
            self.assertSetEqual(expected, actual)
