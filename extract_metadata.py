#!/usr/bin/env python
import base
import datetime
import argparse
import sys
import args
import basejumper.security
import json

parser = args.parser
parser.add_argument("path", help="Path on HPSS system to retrieve metadata of")

argvals = parser.parse_args()
config = args.get_config_module(argvals.config)
bc = base.BASEClient()
path = argvals.path

if not bc.exists(path):
    print "Path '%s' not found." % path
    sys.exit(1)

size = bc.file_size(path)
algo, checksum = bc.file_checksum(path)
modified = bc.file_modified(path)
epoch = datetime.datetime.fromtimestamp(0)
epoch_time = int((modified - epoch).total_seconds())

key = config.daemon_config["BASEJUMP_KEY"]
meta = {"size": size, "path": path, "modified": epoch_time, "hash": checksum, "hash_function": algo}
signature = basejumper.security.get_dict_signature(meta, key)

meta["signature"] = signature

print json.dumps(meta)

