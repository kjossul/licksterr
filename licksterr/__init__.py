import json
import logging
import logging.config
import os
from pathlib import Path

from flask import Flask

from licksterr.models import db, Form
from licksterr.queries import init_db
from licksterr.server import analysis

PROJECT_ROOT = Path(os.path.realpath(__file__)).parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"


def setup_logging(path=os.path.join(ASSETS_DIR, 'logging.json'),
                  default_level=logging.INFO, env_key='LOG_CFG', to_file=True):
    """
    Setup logging configuration
    """
    path = path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
            if not to_file:
                config['root']['handlers'] = ['console']  # keeps only console
                config['handlers'] = {'console': config['handlers']['console']}
            else:
                config['handlers']['info_file_handler']['filename'] = os.path.join(ASSETS_DIR, 'info.log')
                config['handlers']['error_file_handler']['filename'] = os.path.join(ASSETS_DIR, 'error.log')
            config['root']['level'] = 'INFO' if default_level == logging.INFO else 'DEBUG'
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def create_app(config=None):
    # Flask
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config if config else 'config')
    if not config:
        app.config.from_pyfile('config.py')
    app.register_blueprint(analysis)
    # Flask-SQLAlchemy
    app.app_context().push()
    db.init_app(app)
    db.create_all()
    if not len(Form.query.all()):
        init_db()
    return app
