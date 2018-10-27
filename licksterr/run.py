import logging

from licksterr import setup_logging, create_app

setup_logging()
app = create_app()

logger = logging.getLogger(__name__)


def main():
    logger.info("Launching Licksterr")
    app.run()


if __name__ == '__main__':
    main()
