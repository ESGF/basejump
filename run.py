#!/usr/bin/env python

from basejumper.jumper import startd
from basejumper.app import app

startd()
app.run(debug=True)
