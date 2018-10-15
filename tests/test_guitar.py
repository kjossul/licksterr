import operator
import os
import unittest
from collections import defaultdict
from functools import reduce

from mingus.core import scales, notes
from mingus.core.keys import major_keys
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
        self.assertTrue(all(note.value == 0 for note in beat.notes))

    def test_chords(self):
        chord = self.song.guitars[1].measures[0].beats[0].chord
        self.assertEqual('C', chord.name)

    def test_intervals(self):
        intervals = self.song.guitars[2].calculate_intervals()
        expected = {'2': 1, '3': 1, 'b3': 2}
        self.assertDictEqual(expected, intervals)

    def test_interval_form(self):
        matching = Form('G', scales.Ionian, 'E')
        wrong1 = Form('G', scales.Ionian, 'A')
        wrong2 = Form('G', scales.MajorPentatonic, 'E')
        matching_intervals = self.song.guitars[3].calculate_intervals(forms=(matching,))
        wrong1_intervals = self.song.guitars[3].calculate_intervals(forms=(wrong1,))
        wrong2_intervals = self.song.guitars[3].calculate_intervals(forms=(wrong2,))
        self.assertDictEqual({'b2': 2, '2': 5}, matching_intervals)
        self.assertDictEqual({}, wrong1_intervals)
        self.assertDictEqual({'2': 3}, wrong2_intervals)  # only 1-2, 2-3, 5-6

    def test_interval_form_sum(self):
        pass

class TestForm(unittest.TestCase):
    def test_caged(self):
        """CAGED system should find all roots"""
        for key in major_keys:
            expected = Form.GUITAR.get_notes(key)
            actual = defaultdict(set)
            for f in 'CAGED':
                for string, note in Form.get_form_roots(key, f).items():
                    actual[string].add(note)
                    if note < 11:
                        actual[string].add(note + 12)
            actual = {i: tuple(sorted(ns)) for i, ns in actual.items()}
            self.assertDictEqual(expected, actual)

    def test_pentatonic_form(self):
        """Pentatonics should have only 2 notes per string"""
        scale = scales.MinorPentatonic
        key = 'A'
        for f in 'CAGED':
            form = Form(key, scale, f)
            for string, notes in form.notes.items():
                self.assertEqual(2, len(notes))

    def test_locrian_d(self):
        expected = {
            1: [6, 8, 9],
            2: [6, 8, 9],
            3: [5, 6, 8],
            4: [5, 6, 8],
            5: [6, 8],
            6: [6, 8, 9]
        }
        form = Form('G', scales.Locrian, 'D')
        self.assertDictEqual(expected, form.notes)

    def test_sum(self):
        """By chaining two close pentatonics we should get 6 notes per string"""
        scale = scales.MinorPentatonic
        key = 'G'
        f1 = Form(key, scale, 'C')
        f2 = Form(key, scale, 'A')
        f3 = f1 + f2
        f4 = reduce(operator.add, (f1, f2))
        for ns in f3.notes.values():
            self.assertEqual(3, len(ns))
            self.assertDictEqual(f3.notes, f4.notes)

    def test_caged_scales(self):
        """By combining the forms together we should get all the scale notes on each string"""
        keys = ('A',)
        for scale in Form.SUPPORTED:
            for key in keys:
                try:
                    scale_notes = set(scale(key).ascending()[:-1])
                except NoteFormatError:
                    continue
                s = reduce(operator.add, (Form(key, scale, form) for form in 'CAGED'))
                for i, string in Form.GUITAR.strings.items():
                    for n1 in scale_notes:
                        self.assertTrue(any(notes.is_enharmonic(n1, n2)
                                            for n2 in {string[note] for note in s.notes[i]}))