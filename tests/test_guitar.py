import operator
import os
import unittest
from functools import reduce

from mingus.core import scales
from mingus.core.mt_exceptions import NoteFormatError

from licksterr.analyzer import SUPPORTED_SCALES, Parser
from licksterr.guitar import Song, String, Form
from tests import TEST_ASSETS


class TestGuitar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = Parser()
        cls.song = Song(os.path.join(TEST_ASSETS, "test.gp5"))

    def setUp(self):
        self.parser._init_parser()

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
        self.assertTrue(all(note[1] == 0 for note in beat.notes))

    def test_chords(self):
        chord = self.song.guitars[1].measures[0].beats[0].chord
        self.assertEqual('C', chord.name)

    def test_form_matching(self):
        self.parser.parse_track(self.song.guitars[2])
        g_ionian_e = self.parser.forms_db['G']['Ionian']['E']
        g_pentatonic_e = self.parser.forms_db['G']['MajorPentatonic']['E']
        self.assertTrue(len(self.parser.forms_result[g_ionian_e]) == 1)
        self.assertTrue(len(self.parser.forms_result[g_pentatonic_e]) == 0)

    def test_pause(self):
        self.parser.parse_track(self.song.guitars[3])
        g_ionian_e = self.parser.forms_db['G']['Ionian']['E']
        self.assertTrue(len(self.parser.forms_result[g_ionian_e]) == 2)


class TestForm(unittest.TestCase):
    STRINGS = tuple(String(tuning) for tuning in 'EBGDAE')

    def test_g_locrian_d(self):
        expected = {
            1: [6, 8, 9],
            2: [6, 8, 9],
            3: [5, 6, 8],
            4: [5, 6, 8],
            5: [6, 8],
            6: [6, 8, 9]
        }
        self.match_scale(expected, 'G', scales.Locrian, 'D')

    def test_g_locrian_a(self):
        expected = {
            1: [11, 13],
            2: [11, 13, 14],
            3: [10, 12, 13],
            4: [10, 11, 13],
            5: [10, 11, 13],
            6: [11, 13]
        }
        self.match_scale(expected, 'G', scales.Locrian, 'A')

    def test_db_aeolian_d(self):
        expected = {
            1: [11, 12, 14],
            2: [12, 14],
            3: [11, 13, 14],
            4: [11, 13, 14],
            5: [11, 12, 14],
            6: [11, 12, 14]
        }
        self.match_scale(expected, 'Db', scales.Aeolian, 'D')

    def match_scale(self, expected, key, scale, form):
        expected = tuple((string, fret) for string, frets in reversed(list(expected.items())) for fret in frets)
        form = Form.calculate_caged_form(key, scale, form)
        self.assertTupleEqual(expected, form.notes)

    def test_sum(self):
        """By chaining two close pentatonics we should get 3 notes per string"""
        scale = scales.MinorPentatonic
        key = 'G'
        f1 = Form.calculate_caged_form(key, scale, 'C')
        f2 = Form.calculate_caged_form(key, scale, 'A')
        f3 = f1 + f2
        self.assertEqual(3 * 6, len(f3.notes))

    def test_caged_scales(self):
        """By combining the forms together we should get all the scale notes on each string"""
        keys = ('G',)
        for scale in SUPPORTED_SCALES:
            for key in keys:
                try:
                    scale_notes = set(scale(key).ascending()[:-1])
                except NoteFormatError:
                    continue
                sum_form = reduce(operator.add, (Form.calculate_caged_form(key, scale, form, transpose=True)
                                                 for form in 'CAGED'))
                for i, string in enumerate(self.STRINGS, start=1):
                    form_string_notes = tuple(fret for s, fret in sum_form.notes if s == i)
                    self.assertTupleEqual(string.get_notes(scale_notes), form_string_notes)
