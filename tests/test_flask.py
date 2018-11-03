import time
from pathlib import Path

import requests

from licksterr.models import Measure
from tests import TEST_ASSETS, LicksterrTest


class FlaskTest(LicksterrTest):
    def test_file_upload(self):
        url = self.get_server_url() + "/upload"
        filename = Path(TEST_ASSETS) / "test.gp5"
        with open(filename, mode='rb') as f:
            content = f.read()
        files = {'test1.gp5': content, 'test2.gp5': content}
        requests.post(url, files=files)

    def test_track_get(self):
        self.test_file_upload()
        time.sleep(0.3)
        url = self.get_server_url() + "/tracks/1"
        json = requests.get(url).json()
        self.assertTrue('measures' in json)

    def test_measure_match(self):
        self.test_file_upload()
        time.sleep(0.3)
        measure = Measure.query.first()
        url = self.get_server_url() + f"/measures/{measure.id}"
        json = requests.get(url).json()
        self.assertTrue(json)
