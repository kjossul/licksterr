import logging

from flask_testing import LiveServerTestCase
from sqlalchemy.exc import IntegrityError

from licksterr import setup_logging, create_app, db
from licksterr.models import Lick


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

    def test_note(self):
        notes = [[1, 1]]
        lick = Lick(notes=notes)
        db.session.add(lick)
        licks = Lick.query.filter(Lick.contains(1, 1)).all()
        self.assertEqual(1, len(licks))

    def test_lick_uniqueness(self):
        notes = [[1, 1]]
        lick1 = Lick(notes=notes)
        lick2 = Lick(notes=[[1, 1]])
        db.session.add(lick1)
        db.session.commit()
        db.session.add(lick2)
        with self.assertRaises(IntegrityError):
            db.session.commit()

