from args import parser, get_config_module
import hashlib
import hmac
import sys
import requests
import urllib

parser.add_argument("group", metavar="G", type=str, help="Group to associate file with")
parser.add_argument("path", metavar="P", type=str, help="Path to expose")
parser.add_argument("key", metavar="K", type=str, help="Key for path")

vals = parser.parse_args()
config = get_config_module(vals.config)
path = vals.path

try:
    from config import app_config
    key = app_config["PUBLISHER_SECRET_KEY"]
    root = app_config.get("APPLICATION_ROOT", "")
except ImportError, KeyError:
    print "Unable to retrieve secret key for metadata request"
    sys.exit(1)

try:
    from config import host_config
    if "host" in host_config:
        host = host_config["host"]
    else:
        host = "127.0.0.1"

    if "port" in host_config:
        port = host_config["port"]
    else:
        port = 8000
except ImportError:
    host = "127.0.0.1"
    port = 5000

form_data = {"path": path, "key": vals.key}

if port != 80:
    url = "http://{host}:{port}{root}/expose/{group}".format(root=root, host=host, port=port, group=vals.group)
else:
    url = "http://{host}{root}/expose/{group}".format(root=root, host=host, group=vals.group)

print url
response = requests.post(url, data=form_data)
print response.text
