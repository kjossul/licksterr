from licksterr.models import Track
from licksterr.queries import get_track_interval_list
from tests import LicksterrTest


class FlaskTest(LicksterrTest):
    def test_scale_degree_list(self):
        self.upload_file("ks_test_0.gp5")
        track = Track.query.first()
        expected = [[0], [2], [4], [5], [2], [4], [0]]
        actual = get_track_interval_list(track)
        self.assertListEqual(expected, actual)
