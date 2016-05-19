import hmac
import hashlib
import json
import collections


def constant_time_compare(val1, val2):
    # We'll allow them to know that the lengths of the strings don't match
    if len(val1) != len(val2):
        return False

    result = 0
    for x, y in zip(val1, val2):
        result |= ord(x) ^ ord(y)
    return result == 0


def hmac_compare(key, msg, known):
    h = hmac.new(key, msg, hashlib.sha256)
    print h.hexdigest(), known
    return constant_time_compare(h.hexdigest(), known)


def get_dict_signature(dictionary, key):
    h = hmac.new(key, digestmod=hashlib.sha256)
    for k in sorted(dictionary.keys()):
        h.update(k)
        h.update(str(dictionary[k]))
    return h.hexdigest()


def check_json_sig(dictionary, key, signature):
    return constant_time_compare(get_dict_signature(dictionary, key), signature)


def sign_path(path, key):
    h = hmac.new(key, path, hashlib.sha256)
    return h.hexdigest()
