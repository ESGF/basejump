#!/usr/bin/env python

import json
import requests
import args
import basejumper
import sys

parser = args.parser
parser.add_argument("--cert", nargs=1, help="Certificate Authority to use; set to false to ignore SSL errors")
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

if a.cert:
    cert = a.cert[0]
    if cert.lower() == "false":
         cert = False
else:
    cert = None

print "Posting to:", config.daemon_config["BASEJUMP_FRONTEND_URL"] + "/expose/" + a.group
r = requests.post(config.daemon_config["BASEJUMP_FRONTEND_URL"] + "/expose/" + a.group, data=data, verify=cert)
try:
    r.json()
    print r.json()["queue_url"]
except ValueError:
    print "No JSON found in response:"
    print r.content

