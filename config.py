from pathlib import Path

# Paths
PROJECT_DIR = "/srv/www/licksterr"
UPLOAD_DIR = Path(PROJECT_DIR) / "uploads"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)