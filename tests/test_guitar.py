import operator
import os
import unittest
from functools import reduce

from mingus.core import scales
from mingus.core.mt_exceptions import NoteFormatError

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
        self.assertTrue(all(note.fret == 0 for note in beat.notes))

    def test_chords(self):
        chord = self.song.guitars[1].measures[0].beats[0].chord
        self.assertEqual('C', chord.name)



class TestForm(unittest.TestCase):

    def test_pentatonic_form(self):
        """Pentatonics should have only 2 notes per string"""
        scale = scales.MinorPentatonic
        key = 'G'
        for f in 'CAGED':
            form = Form(key, scale, f)
            for string in range(1, 7):
                self.assertEqual(2, len([note for note in form.notes if note.string == string]))

    def test_d_locrian(self):
        d_locrian = {
            1: [6, 8, 9],
            2: [6, 8, 9],
            3: [5, 6, 8],
            4: [5, 6, 8],
            5: [6, 8],
            6: [6, 8, 9]
        }
        s = Form._STRINGS
        expected = [s[string-1].notes[fret] for string, frets in reversed(list(d_locrian.items())) for fret in frets]
        form = Form('G', scales.Locrian, 'D')
        self.assertListEqual(expected, form.notes)

    def test_sum(self):
        """By chaining two close pentatonics we should get 3 notes per string"""
        scale = scales.MinorPentatonic
        key = 'G'
        f1 = Form(key, scale, 'C')
        f2 = Form(key, scale, 'A')
        f3 = f1 + f2
        for string in range(1, 7):
            self.assertEqual(3, len([note for note in f3.notes if note.string == string]))

    def test_caged_scales(self):
        """By combining the forms together we should get all the scale notes on each string"""
        keys = ('A',)
        for scale in Form.SUPPORTED_SCALES:
            for key in keys:
                try:
                    scale_notes = set(scale(key).ascending()[:-1])
                except NoteFormatError:
                    continue
                s = reduce(operator.add, (Form(key, scale, form) for form in 'CAGED'))
                for string in Form._STRINGS:
                    form_string_notes = set(note for note in s.notes if note.string == string.index)
                    self.assertTrue(form_string_notes.issubset(string.get_notes((scale_notes))))