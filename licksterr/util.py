import logging
from functools import wraps
from time import time

logger = logging.getLogger(__name__)


def timing(f, level=logging.DEBUG, verbose=False):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        args_description = f"args:[{args}, {kw}]" if verbose else ''
        logger.log(level, f'func:{f.__name__} {args_description} took: {te-ts:2.4f}sec')
        return result

    return wrap


def row2dict(row):
    d = {}
    for column in row.__table__.columns:
        d[column.name] = str(getattr(row, column.name))

    return d
