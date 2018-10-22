from pathlib import Path

import requests

from tests import TEST_ASSETS, LicksterrTest


class FlaskTest(LicksterrTest):
    def test_file_upload(self):
        url = self.get_server_url() + "/upload"
        filename = Path(TEST_ASSETS) / "test.gp5"
        with open(filename, mode='rb') as f:
            content = f.read()
        files = {'test1.gp5': content, 'test2.gp5': content}
        requests.post(url, files=files)
