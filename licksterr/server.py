import logging

from flask import Blueprint, render_template, request, abort, current_app, send_file, send_from_directory

from licksterr.models import Song, Track, TrackMeasure

logger = logging.getLogger(__name__)
navigator = Blueprint('navigator', __name__)


@navigator.route('/')
def home():
    songs = {song: song.to_dict() for song in Song.query.all()}
    return render_template('home.html', songs=songs), "HTTP/1.1 200 OK", {"Content-Type": "text/html"}


@navigator.route('/player', methods=['GET'])
def player():
    song_id = request.args.get("song")
    song = Song.query.get(song_id)
    if not song:
        abort(404)
    analyzed_tracks = {track.index: track.id for track in song.tracks}
    filename = f"tabs/{song_id}"
    return render_template('player.html', song=song, filename=filename,
                           analyzed_tracks=analyzed_tracks), "HTTP/1.1 200 OK", {"Content-Type": "text/html"}


@navigator.route('/tabs/<tab_id>')
def get_tab(tab_id):
    # todo use nginx to send static files instead
    tab_folder = current_app.config['UPLOAD_DIR']
    return send_from_directory(tab_folder, tab_id)
