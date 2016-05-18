from flask import request
from functools import wraps
import inspect
import urlparse


def get_keyword_argument_names(func):
    args, varargs, kwargs, defaults = inspect.getargspec(func)
    keyword_names = args[-len(defaults):]
    return keyword_names


def querykeys(f):
    # Inspect f to determine keyword args
    keyword_names = get_keyword_argument_names(f)

    @wraps(f)
    def wrapped(*args):
        query_args = urlparse.parse_qs(request.query_string)
        my_args = {}
        for arg in query_args:
            if arg not in keyword_names:
                raise TypeError("Unexpected query parameter %s; expected args: %s" % (arg, repr(keyword_names)))
            if len(query_args[arg]) == 1:
                my_args[arg] = query_args[arg][0]
            else:
                my_args[arg] = query_args[arg]
        return f(*args, **my_args)
    return wrapped
