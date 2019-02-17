import logging

from flask import Blueprint, render_template, request, abort, current_app, send_file

from licksterr.models import Song, Track, TrackMeasure

logger = logging.getLogger(__name__)
navigator = Blueprint('navigator', __name__)


@navigator.route('/', defaults={'req_path': ''})
@navigator.route('/<path:req_path>')
def home(req_path):
    # fixme ask for feedback if this is a security issue (is blacklisting '..' enough?)
    if req_path.startswith(str(current_app.config['PROJECT_DIR'])[1:]) and not '..' in req_path:
        if not '..' in req_path:
            return get_file("/" + req_path)  # fixme platform independency (/ works only for unix?)
        else:
            abort(423)  # Locked
    # Else render the homepage
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
    img_dir = current_app.config['SHAPES_DIR']
    measure_info = TrackMeasure.get_measure_dictionary(track)
    return render_template('player.html', song=song, filename=filename, track_index=track.index,
                           interval_list=track.intervals, measure_info=measure_info,
                           img_dir=img_dir), "HTTP/1.1 200 OK", {"Content-Type": "text/html"}


def get_file(filename):
    return send_file(filename)
