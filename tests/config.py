import os
from pathlib import Path

from sqlalchemy.pool import NullPool

TESTING = True
DEBUG = True
# Paths
PROJECT_DIR = Path(os.path.realpath(__name__)).parents[0] / "licksterr"
UPLOAD_DIR = Path(PROJECT_DIR) / "uploads"
ASSETS_DIR = Path(PROJECT_DIR) / "assets"
SHAPES_DIR = ASSETS_DIR / "shapes"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
SHAPES_DIR.mkdir(exist_ok=True)

# This db is already initiated with notes and forms (since they take almost 30s to compute)
DB_USER = 'licksterr-test'
DB_PASSWORD = 'test'
DB_IP = 'localhost'
DB_PORT = 5432
DB_DB = 'licksterr-test'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_IP}:{DB_PORT}/{DB_DB}"
SQLALCHEMY_ENGINE_OPTIONS = {
    'poolclass': NullPool
}
