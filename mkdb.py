#!/usr/bin/env python
import basejumper.db
from args import parser, get_config_module

vals = parser.parse_args()
config = get_config_module(vals.config)

try:
    from config import db_config
    db = basejumper.db.DB(db_config)
    db.initdb()
except ImportError:
    print "Could not import db_config from config.py."
except KeyError:
    print "Could not find necessary keys in db_config; we need type and url."
