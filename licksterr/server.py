import logging

from flask import Blueprint

logger = logging.getLogger(__name__)
navigator = Blueprint('navigator', __name__)


@navigator.route('/', methods=['GET'])
def home():
    return "Hello, world!"
