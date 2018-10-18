import os
from pathlib import Path

TESTING = True
DEBUG = True
# Paths
PROJECT_DIR = Path(os.path.realpath(__name__)).parents[0] / ".caged"
UPLOAD_DIR = Path(PROJECT_DIR) / "uploads"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


DB_USER = 'caged-test'
DB_PASSWORD = 'test'
DB_IP = 'localhost'
DB_PORT = 5432
DB_DB = 'caged-test'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_IP}:{DB_PORT}/{DB_DB}"
