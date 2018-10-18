import logging

from flask_testing import TestCase

from src import setup_logging, create_app


class MyTest(TestCase):

    def create_app(self):
        setup_logging(to_file=False)
        app = create_app(config='tests/config')
        self.logger = logging.getLogger(__name__)
        return app

    def test_upload(self):
        pass