import logging
from pathlib import Path

from flask_testing import LiveServerTestCase
from sqlalchemy import text

from licksterr import ASSETS_DIR, db, setup_logging, create_app

TEST_ASSETS = Path(ASSETS_DIR) / "tests"


class LicksterrTest(LiveServerTestCase):
    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        for table in db.metadata.tables:
            if table not in ('form', 'note', 'form_note'):
                db.engine.execute(text('DROP TABLE %s CASCADE' % table))

    def create_app(self):
        setup_logging(to_file=False, default_level=logging.DEBUG)
        app = create_app(config='tests.config')
        self.logger = logging.getLogger(__name__)
        return app
