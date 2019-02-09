import logging

from flask import Blueprint, render_template, request, abort, current_app, send_file

from licksterr.models import Song, Track
from licksterr.queries import get_track_interval_list

logger = logging.getLogger(__name__)
navigator = Blueprint('navigator', __name__)


@navigator.route('/', defaults={'req_path': ''})
@navigator.route('/<path:req_path>')
def home(req_path):
    if req_path.startswith(str(current_app.config['UPLOAD_DIR'])[1:]):
        return get_file("/" + req_path)  # fixme platform independency (/ works only for unix?)
    songs = {song: song.to_dict() for song in Song.query.all()}
    return render_template('home.html', songs=songs), "HTTP/1.1 200 OK", {"Content-Type": "text/html"}


@navigator.route('/player', methods=['GET'])
def player():
    track_id = request.args.get("track")
    track = Track.query.get(track_id)
    if not track:
        abort(404)
    song = Song.query.get(track.song_id)
    filename = str(current_app.config['UPLOAD_DIR'] / (str(track.song_id)))
    interval_list = get_track_interval_list(track, include_rests=False, include_ties=False)
    return render_template('player.html', song=song, filename=filename, track_index=track.index,
                           interval_list=interval_list), "HTTP/1.1 200 OK", {"Content-Type": "text/html"}


def get_file(filename):
    return send_file(filename)
