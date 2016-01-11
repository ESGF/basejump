from base import BASEClient
import os
import random
import time
import hashlib

__client__ = BASEClient()


def file_metadata(path):
    key = file_key(path)
    if key is None:
        raise ValueError("Invalid File")
    random.seed(key)
    filesize = random.randint(1000, 10000)
    return {"key": key, "size": __client__.file_size(path), "hash": None}


def stream_file(path, destination):
    if file_key(path) is None:
        raise ValueError("Path '%s' does not exist" % path)
    chunk_size = 100
    tape_delay = 10
    for progress, filesize in __client__.stream_file(path, destination):
        yield int(100 * float(progress) / filesize)


def file_key(path):
    """
    Determines if file exists (returns None if it does not) and generates the
    key used for referring to the file in the DB
    """
    if path is None:
        return None
    if not __client__.exists(path):
        return None
    return hashlib.sha256(path)
