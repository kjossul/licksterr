import os

import requests

from licksterr.models import Measure, Song, Track, Beat
from tests import LicksterrTest


class FlaskTest(LicksterrTest):
    def test_track_get(self):
        self.upload_file()
        url = self.get_server_url() + "/tracks/1"
        json = requests.get(url).json()
        self.logger.info(json)
        self.assertEqual(1, len(json['keys']))

    def test_measure(self):
        self.upload_file()
        # two identical measures should produce a single row in the database
        self.assertEqual(1, len(Measure.query.all()))
        # only 4 beats should be generated
        self.assertEqual(4, len(Beat.query.all()))

    def test_multiple_upload(self):
        self.upload_file()
        self.upload_file()
        files = [name for name in os.listdir(self.app.config['UPLOAD_DIR'])]
        self.assertEqual(1, len(files))

    def test_wrong_file(self):
        response = self.upload_file("wrong_file.gp5")
        self.assertEqual(400, response.status_code)

    def test_song_delete(self):
        self.upload_file()
        delete_url = self.get_server_url() + '/songs/1'
        requests.delete(delete_url)
        self.assertFalse(Song.query.all())
        self.assertFalse(Track.query.all())
        files = [name for name in os.listdir(self.app.config['UPLOAD_DIR'])]
        self.assertEqual(0, len(files))
