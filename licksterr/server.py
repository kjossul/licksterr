import logging

from flask import Blueprint, render_template, request, abort, current_app

from licksterr.models import Song, Track
from licksterr.queries import get_track_interval_list

logger = logging.getLogger(__name__)
navigator = Blueprint('navigator', __name__)


@navigator.route('/', methods=['GET'])
def home():
    songs = {song: song.to_dict() for song in Song.query.all()}
    return render_template('home.html', songs=songs), "HTTP/1.1 200 OK", {"Content-Type": "text/html"}


@navigator.route('/reader', methods=['GET'])
def viewer():
    track_id = request.args.get("track")
    track = Track.query.get(track_id)
    if not track:
        abort(404)
    filename = str(current_app.config['UPLOAD_DIR'] / (str(track.song_id)))
    interval_list = get_track_interval_list(track.song_id)
    return render_template('reader.html', filename=filename, interval_list=interval_list), "HTTP/1.1 200 OK", {
        "Content-Type": "text/html"}
