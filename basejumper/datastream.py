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

    check_result = __client__.file_checksum(path)
    if check_result is None:
        checksum_type = None
        checksum = None
    else:
        checksum_type, checksum = check_result

    last_modified = __client__.file_modified(path)
    # Convert last_modified to ISO 8601
    last_modified = last_modified.isoformat()
    return {"key": key, "size": __client__.file_size(path), "hash": checksum, "hash_function": checksum_type, "modified": last_modified}


def stream_file(path, destination):
    if file_key(path) is None:
        raise ValueError("Path '%s' does not exist" % path)

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
    return hashlib.sha256(path).hexdigest()
