import json
import logging
import logging.config
import os
from pathlib import Path

ASSETS_FOLDER = os.path.join(Path(os.path.realpath(__file__)).parents[1], "assets")


def setup_logging(path=os.path.join(ASSETS_FOLDER, 'logging.json'),
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
                config['handlers']['info_file_handler']['filename'] = os.path.join(ASSETS_FOLDER, 'info.log')
                config['handlers']['error_file_handler']['filename'] = os.path.join(ASSETS_FOLDER, 'error.log')
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)
