import os
import unittest

from src import ASSETS_FOLDER
from src.parser import Analyzer


class TestParser(unittest.TestCase):
    TEST_ASSETS = os.path.join(ASSETS_FOLDER, "tests")

    @classmethod
    def setUpClass(cls):
        cls.analyzer = Analyzer(os.path.join(cls.TEST_ASSETS, "test.gp5"))

    def test_tracks(self):
        self.assertEqual(7, len(self.analyzer.guitars))  # all tracks should be loaded

    def test_notes(self):
        # all strings are strummed on zero exactly once
        self.assertTrue(all(string.count_hits()[0] == 1 for string in self.analyzer.guitars[0].strings.values()))
