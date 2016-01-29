#!/usr/bin/env python
from args import parser, get_config_module
from proxy_middleware import ReverseProxied

vals = parser.parse_args()
config = get_config_module(vals.config)

from basejumper.jumper import startd
from basejumper.app import configure

startd(config)
app = configure(config)

try:
    from config import host_config

    if "hostname" in host_config:
        host = host_config["hostname"]
    else:
        host = "127.0.0.1"

    if "port" in host_config:
        port = host_config["port"]
    else:
        port = 8000

    #app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.run(host, port)
except ImportError:
    app.run()
