import os
import random
import time
import hashlib


def file_metadata(path):
    key = file_key(path)
    if key is None:
        raise ValueError("Invalid File")
    random.seed(key)
    filesize = random.randint(1000, 10000)
    return {"key": key, "size": filesize, "hash": None}


def stream_file(path):
    filesize = file_metadata(path)["size"]
    chunk_size = 100
    tape_delay = 10
    for i in range(0, filesize, chunk_size):
        d = os.urandom(chunk_size)
        r = random.random() * tape_delay
        time.sleep(r)
        yield d
        # TODO: Update DB progress for this key


def file_key(path):
    """
    Determines if file exists (returns None if it does not) and generates the
    key used for referring to the file in the DB
    """
    if path is None:
        return None
    hasher = hashlib.md5()
    hasher.update(path)
    # TODO: Should use a secret key to prevent simple attack vectors
    key = hasher.hexdigest()
    return key
