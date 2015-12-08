import os
import random
import time
import hashlib
import tempfile


def stream_file(path):
    hasher = hashlib.md5()
    hasher.update(path)
    key = hasher.hexdigest()
    random.seed(key)
    filesize = random.randint(1000, 10000)
    chunk_size = 100
    tape_delay = 1
    for i in range(0, filesize, chunk_size):
        d = os.urandom(chunk_size)
        r = random.random() * tape_delay
        time.sleep(r)
        yield d


def get_file(path):
    temp = tempfile.NamedTemporaryFile()
    for chunk in stream_file(path):
        temp.write(chunk)
    return temp


def file_key(path):
    if path is None:
        return None
    hasher = hashlib.md5()
    hasher.update(path)
    key = hasher.hexdigest()
    return key
