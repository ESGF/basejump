#!/usr/bin/env python

import json
import requests
import args
import basejumper
import sys

parser = args.parser
parser.add_argument("group", help="ESGF group to associate data with")
a = parser.parse_args()
config = args.get_config_module(a.config)

vals = json.load(sys.stdin)
data = {}
for k in "path", "size", "hash", "hash_function", "modified", "signature":
    data[k] = vals.get(k, None)
    if data[k] is None:
        print "No %s provided." % k
        sys.exit(1)

r = requests.post(config.daemon_config["BASEJUMP_FRONTEND_URL"] + "/expose/" + a.group, data=data)
print r.json()["queue_url"]

