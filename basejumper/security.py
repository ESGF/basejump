import hmac
import hashlib


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
    return constant_time_compare(h.hexdigest(), known)
