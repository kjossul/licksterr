import logging
import os

from flask import Blueprint, request, flash
from flask import current_app as app
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)
analysis = Blueprint('analysis', __name__)

ALLOWED_EXTENSIONS = {'gp3', 'gp4', 'gp5'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@analysis.route('/upload', methods=['POST'])
def upload_file():
    # check if the post request has the file part
    for file in request.files:
        pass  # todo store tab here
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app['UPLOAD_FOLDER'], filename))

