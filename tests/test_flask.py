import logging
from pathlib import Path

import requests
from flask_testing import LiveServerTestCase

from cagedfinder import setup_logging, create_app, db
from tests import TEST_ASSETS


class MyTest(LiveServerTestCase):
    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        setup_logging(to_file=False)
        app = create_app(config='tests.config')
        self.logger = logging.getLogger(__name__)
        return app

    def test_file_upload(self):
        url = self.get_server_url() + "/upload"
        filename = Path(TEST_ASSETS) / "test.gp5"
        with open(filename, mode='rb') as f:
            content = f.read()
        files = {'test1.gp5': content, 'test2.gp5': content}
        requests.post(url, files=files)
