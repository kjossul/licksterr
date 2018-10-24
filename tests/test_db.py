import logging

from licksterr.analyzer import parse_song
from licksterr.models import Form, Scale, Note, Measure
from tests import LicksterrTest

logger = logging.getLogger(__name__)

class TestDatabase(LicksterrTest):
    def test_db_init(self):
        notes = Note.query.all()
        forms = Form.query.all()
        self.assertEqual(6 * 30, len(notes))
        self.assertEqual(len(Scale) * 12 * 5, len(forms))

    def test_song_parsing(self):
        parse_song("tests/test.gp5")
        # two identical measures should produce a single row in the database
        self.assertEqual(1, len(Measure.query.all()))

