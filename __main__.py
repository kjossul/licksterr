from licksterr import setup_logging, create_app

setup_logging()
app = create_app()

if __name__ == '__main__':
    app.run()
