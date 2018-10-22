import logging

from flask_testing import LiveServerTestCase

from licksterr import setup_logging, create_app, db
from licksterr.models import Form, Scale, Note


class TestDatabase(LiveServerTestCase):
    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        setup_logging(to_file=False, default_level=logging.DEBUG)
        app = create_app(config='tests.config')
        self.logger = logging.getLogger(__name__)
        return app

    def test_db_init(self):
        notes = Note.query.all()
        forms = Form.query.all()
        self.assertEqual(6 * 30, len(notes))
        self.assertEqual(len(Scale) * 12 * 5, len(forms))
