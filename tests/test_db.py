import logging

from flask_testing import LiveServerTestCase
from sqlalchemy.exc import IntegrityError

from licksterr import setup_logging, create_app, db
from licksterr.models import Lick, Form, Scale, form_lick
from licksterr.queries import init_forms


class TestDatabase(LiveServerTestCase):
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
        self.assertFalse(self.form.licks)
        self.form.licks.append(self.lick)
        db.session.commit()
        self.assertTrue(Form.query.get(1).licks)
        self.assertTrue(db.session.query(form_lick).all())
        db.session.delete(self.lick)
        db.session.commit()
        self.assertFalse(Form.query.get(1).licks)
        self.assertFalse(db.session.query(form_lick).all())

    def test_form_init(self):
        init_forms()
        forms = Form.query.all()
        self.assertEqual(len(Scale) * 12 * 31, len(forms))