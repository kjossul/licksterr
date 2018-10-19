import logging

from flask_testing import LiveServerTestCase
from sqlalchemy.exc import IntegrityError

from licksterr import setup_logging, create_app, db
from licksterr.models import Lick, Form, Scale


class MyTest(LiveServerTestCase):
    def setUp(self):
        db.create_all()
        self.notes = [[1, 1]]
        self.lick = Lick(notes=self.notes)
        self.form = Form(key=0, scale=Scale.IONIAN, name='C', notes=self.notes)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        setup_logging(to_file=False)
        app = create_app(config='tests.config')
        self.logger = logging.getLogger(__name__)
        return app

    def test_note(self):
        db.session.add(self.lick)
        match = Lick.query.filter(Lick.contains(1, 1)).first()
        no_match = Lick.query.filter(Lick.contains(1, 2)).first()
        self.assertTrue(match)
        self.assertFalse(no_match)

    def test_lick_uniqueness(self):
        lick2 = Lick(notes=self.notes)
        db.session.add(self.lick)
        db.session.commit()
        db.session.add(lick2)
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def test_association_delete(self):
        db.session.add(self.form)
        form = Form.query.get(1)
        self.assertFalse(form.licks)
        form.licks.append(self.lick)
        lick = Lick.query.get(1)
        self.assertTrue(lick)