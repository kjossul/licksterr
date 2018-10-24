import logging
import os

from flask import Blueprint, request, abort
from flask import current_app as app
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)
navigator = Blueprint('navigator', __name__)
analysis = Blueprint('analysis', __name__)

ALLOWED_EXTENSIONS = {'gp3', 'gp4', 'gp5'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@navigator.route('/', methods=['GET'])
def home():
    return "Hello, world!"


@analysis.route('/upload', methods=['POST'])
def upload_file():
    if not request.files:
        abort(400)
    for filename, file in request.files.items():
        if file and allowed_file(filename):
            filename = secure_filename(filename)
            dest = os.path.join(app.config['UPLOAD_DIR'], filename)
            logger.info(f"Saving file to {dest}")
            file.save(dest)
    return "OK"
