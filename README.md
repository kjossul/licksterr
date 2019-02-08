# Licksterr

A platform that helps you find songs in order to exercise a specific scale box on the guitar fretboard.

The project goal is to parse `.gp*` files and extract information on scales and forms used inside the track.

## Dependencies
* [Flask](http://flask.pocoo.org/) + [SqlAlchemy](https://www.sqlalchemy.org/) + [Postgresql](https://www.postgresql.org/)
*  [PyGuitarPro](https://github.com/Perlence/PyGuitarPro) (a Python port of 
[AlphaTab](https://www.alphatab.net/documentation/)) for server-side analysis and AlphaTab for tab rendering.
* [My Mingus (Python3 port + scale additions)](https://github.com/NonSvizzero/python-mingus) 


## Installation instructions

After cloning this repo and installing all the dependencies, create an [instance folder](http://flask.pocoo.org/docs/0.12/config/#instance-folders) in this directory to store configuration files.
`config.py` should hold SQLAlchemy configuration (that matches your PostgreSql installation) and `licksterr.ini` stores
parameters related to uwsgi. 

A sample configuration could be as follows:

`instance/config.py`:
```python
from pathlib import Path

# Paths
PROJECT_DIR = "/srv/www/licksterr"
UPLOAD_DIR = Path(PROJECT_DIR) / "uploads"
TEMP_DIR = Path(PROJECT_DIR) / "temp"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

DB_USER = 'licksterr'
DB_PASSWORD = 'licksterr'
DB_IP = 'localhost'
DB_PORT = 5432
DB_DB = 'licksterr'

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_IP}:{DB_PORT}/{DB_DB}"

```
A new user named `licksterr` should be created in your PostgreSql installation following the example above. A way to do 
it is the following:

1. Log in as the postgres user : `$ sudo -u postgres`
2. Create a new user: `$ createuser licksterr --pwprompt` 
3. Create a new database for the user: `$ createdb -O licksterr licksterr` 

As long as the identifiers match the ones in the `config.py` file, the application should work fine.

`instance/licksterr.ini`
```ini
[uwsgi]
module = licksterr.run:app

master = true
processes = 5

socket = licksterr.sock
chmod-socket = 660
vacuum = true

die-on-term = true
```
