import logging

from flask import Blueprint, render_template

from licksterr.models import Song

logger = logging.getLogger(__name__)
navigator = Blueprint('navigator', __name__)


@navigator.route('/', methods=['GET'])
def home():
    songs = {song: [track.to_dict() for track in song.tracks] for song in Song.query.all()}
    return render_template('home.html', songs=songs), "HTTP/1.1 200 OK", {"Content-Type": "text/html"}
