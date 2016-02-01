from args import parser, get_config_module
import hashlib
import hmac
import sys
import requests
import urllib

parser.add_argument("path", metavar="P", type=str, help="Path to query metadata of")
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

digest = hmac.new(key, path, hashlib.sha256).hexdigest()

query = urllib.urlencode({"path": path, "digest": digest})

url = "http://{host}:{port}{root}/metadata?{query}".format(root=root, host=host, port=port, query=query)
print url
response = requests.get(url)
print response.text
