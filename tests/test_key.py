import requests

from licksterr.models import NOTES_DICT
from tests import LicksterrTest


class FlaskTest(LicksterrTest):

    def test_ks_0(self):
        self.match_scale("ks_test_0.gp5", 0, 'C', True, 'IONIAN')

    def test_ks_1(self):
        self.match_scale("ks_test_1.gp5", 0, 'C', True, 'MAJORPENTATONIC')

    def test_wywh(self):
        self.match_scale("wish_you_were_here.gp5", 2, 'G', True, 'IONIAN')

    def test_mad_world(self):
        self.match_scale("mad_world.gp5", 2, 'F', False, 'DORIAN')

    def match_scale(self, filename, track, key, is_major, scale):
        self.upload_file(filename, tracks=[track])
        url = self.get_server_url() + f"/tracks/1"
        json = requests.get(url).json()
        d = json['scale']
        self.assertEqual(NOTES_DICT[key], d['key'])
        self.assertEqual(is_major, d['is_major'])
        self.assertEqual(scale, d['name'])
