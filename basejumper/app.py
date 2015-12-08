from flask import Flask, request, jsonify
from addons import querykeys
from mock import datastream
app = Flask(__name__)

@app.route("/")
def main():
    return "Nothing to see here..."


@app.route("/queue")
@querykeys
def queue_job(path=None):
    """
    /queue?path=/path/to/data/on/server ->
        Authenticate Session w/ESGF
        Verify Permissions w/ESGF
        Check File Exists
        Queue in DB
    """
    # Validate arguments
    if path is None:
        raise ValueError("No path provided")
    print path
    # Authenticate User
    # TODO: Implement
    pass
    # Verify Permissions
    # TODO: Implement
    pass
    # Check File Exists, retrieve key
    ### We should use a secret key in generating this key
    ### Should we also use a credential-associated key?
    key = datastream.file_key(path)
    if not key:
        raise ValueError("File %s not found." % (path))
    # Queue in DB
    # TODO: Implement
    return jsonify({"key": key, "progress": "/progress/%s" % key})

if __name__ == "__main__":
    app.debug = True
    app.run()
