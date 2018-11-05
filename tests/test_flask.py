import os

import requests

from licksterr.models import Measure
from tests import TEST_ASSETS, LicksterrTest


class FlaskTest(LicksterrTest):
    def test_file_upload(self, filename=TEST_ASSETS / "test.gp5"):
        url = self.get_server_url() + "/upload"
        with open(filename, mode='rb') as f:
            content = f.read()
        files = {os.path.basename(filename): content}
        requests.post(url, files=files)

    def test_track_get(self):
        self.test_file_upload()
        url = self.get_server_url() + "/tracks/1"
        json = requests.get(url).json()
        self.assertEqual(1, len(json['match']))

    def test_measure_match(self):
        self.test_file_upload()
        measure = Measure.query.first()
        url = self.get_server_url() + f"/measures/{measure.id}"
        json = requests.get(url).json()
        self.assertTrue(json)

    def test_multiple_upload(self):
        self.test_file_upload()
        self.test_file_upload()
        files = [name for name in os.listdir(self.app.config['UPLOAD_DIR'])]
        self.assertEqual(1, len(files))

    def test_wywh(self):
        """Best match for wish you were here solo track should be G IONIAN, G form"""
        self.test_file_upload(TEST_ASSETS / "wish_you_were_here.gp5")
        url = self.get_server_url() + f"/tracks/2"  # solo guitar
        json = requests.get(url).json()
        self.logger.info(json['match'])
        self.assertEqual(7, json['match'][0]['key'])
        self.assertEqual('IONIAN', json['match'][0]['scale'])
