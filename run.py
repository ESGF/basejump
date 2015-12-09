#!/usr/bin/env python
from args import config

from basejumper.jumper import startd
from basejumper.app import configure

startd(config)
app = configure(config)
app.run()
