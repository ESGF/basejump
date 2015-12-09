from flask import Flask, request, jsonify
from addons import querykeys
from mock import datastream
import db
from models import Transfer

app = Flask(__name__)

database = None
session = None


@app.route("/")
def main():
    return "BASEJumper Alpha"


@app.route("/progress/<key>")
def job_progress(key):
    """
    /progress/hashed_path_with_key ->
        Find the specified job
        Return the progress
    """
    with session() as s:
        for t in s.query(Transfer).filter(Transfer.key == key):
            progress = t.progress
            break
        else:
            raise ValueError("Invalid key %s provided" % key)
        s.close()
    return jsonify({"progress": progress, "key":key})


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
    # Authenticate User
    # TODO: Implement
    pass
    # Verify Permissions
    # TODO: Implement
    pass
    # Check File Exists, retrieve key
    ### We should use a secret key in generating this key
    key = datastream.file_key(path)
    if not key:
        raise ValueError("File %s not found." % (path))

    with session() as s:
        # Check if already queued
        for t in s.query(Transfer).filter(Transfer.path == path):
            # Check if there's an existing transfer for this file
            break
        else:
            # Queue in DB using path
            t = Transfer(path=path, key=key, progress=0)
            s.add(t)
            s.commit()

    return jsonify({"key": key, "progress": "/progress/%s" % key})


def configure(config):
    global database
    database = db.DB(config.db_config) 
    global session
    session = database.session
    app.config.update(config.app_config)
    return app
