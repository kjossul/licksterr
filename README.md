# CAGED Finder

A platform that helps you find songs in order to exercise a specific scale box on the guitar fretboard.

The project goal is to parse `.gp*` files and extract information on scales and forms used inside the track.

## Dependencies
* [Flask](http://flask.pocoo.org/) + [SqlAlchemy](https://www.sqlalchemy.org/) + [PostGreSql](https://www.postgresql.org/)
*  [PyGuitarPro](https://github.com/Perlence/PyGuitarPro) (a Python port of 
[AlphaTab](https://www.alphatab.net/documentation/)).
* [Mingus (Python3 port + scale additions)](https://github.com/NonSvizzero/python-mingus) 