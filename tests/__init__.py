import json
import logging
import os
from pathlib import Path

import requests
from flask_testing import LiveServerTestCase
from sqlalchemy import text

from licksterr import ASSETS_DIR, db, setup_logging, create_app

TEST_ASSETS = Path(ASSETS_DIR) / "tests"


class LicksterrTest(LiveServerTestCase):
    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        # keeps scales and notes created at startup
        for table in db.metadata.tables:
            db.engine.execute(text('DROP TABLE %s CASCADE' % table))

    def create_app(self):
        setup_logging(to_file=False, default_level=logging.DEBUG)
        app = create_app(config='tests.config')
        self.logger = logging.getLogger(__name__)
        return app

    def upload_file(self, filename="test.gp5", tracks=None):
        file = TEST_ASSETS / filename
        url = self.get_server_url() + "/upload"
        tracks = [0] if not tracks else tracks
        with open(file, mode='rb') as f:
            content = f.read()
        files = {os.path.basename(file): content}
        return requests.post(url, files=files, data={'tracks': json.dumps(tracks)})
