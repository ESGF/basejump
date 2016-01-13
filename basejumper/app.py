from flask import Flask, request, jsonify
from addons import querykeys
import datastream
import db
from models import Transfer, File
import security
from datetime import datetime

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
        for t in s.query(Transfer).join(Transfer.file).filter(File.key == key).all():
            progress = t.progress
            break
        else:
            raise ValueError("Invalid key %s provided" % key)
        s.close()
    return jsonify({"progress": progress, "key": key})


@app.route("/metadata")
@querykeys
def file_metadata(path=None, digest=None):
    digest_error = "Valid digest must be provided to retrieve metadata"

    matches = security.hmac_compare(app.config["PUBLISHER_SECRET_KEY"], path, digest)

    if not matches:
        raise ValueError(digest_error)

    # Now we can actually retrieve the metadata
    meta = datastream.file_metadata(path)

    return jsonify(meta)


@app.route("/expose", methods=["POST"])
def expose_path():
    if "path" not in request.form or "key" not in request.form:
        raise ValueError("Path and Key are required to expose a path")
    path, key = request.form["path"], request.form["key"]
    test_key = datastream.file_key(path)
    print test_key, key, path
    matches = security.constant_time_compare(test_key, key)

    if not matches:
        raise ValueError("Key is invalid for provided path")

    meta = datastream.file_metadata(path)
    with session() as s:
        f = s.query(File).filter(File.key == key).all()
        if f:
            raise ValueError("This path is already exposed.")

        last_modified = datetime.fromtimestamp(meta["modified"])
        f = File(path=path, key=key, size=meta["size"], checksum=meta["hash"], checksumType=meta["hash_function"], modified=last_modified)
        s.add(f)
        s.commit()
    url_path = f.queue_url()
    url = request.url_root + url_path
    return jsonify({"queue_url": url})


@app.route("/queue/<key>")
def queue_job(key):
    """
    /queue?path=/path/to/data/on/server ->
        Authenticate Session w/ESGF
        Verify Permissions w/ESGF
        Check File Exists
        Queue in DB
    """
    if key is None:
        raise ValueError("No key provided.")

    # Authenticate User
    # TODO: Implement
    pass

    with session() as s:

        f = s.query(File).filter(File.key == key)
        if not f:
            raise ValueError("No file matching key exposed.")

        f = f[0]

        # Verify Permissions
        # TODO: Implement
        pass

        # Check if already queued
        for t in s.query(Transfer).filter(Transfer.file == f):
            # Check if there's an existing transfer for this file
            break
        else:
            # Queue transfer in DB
            t = Transfer(file=f, progress=0)
            s.add(t)
            s.commit()

    return jsonify({"progress": "/progress/%s" % key})


def configure(config):
    global database
    database = db.DB(config.db_config)
    global session
    session = database.session
    app.config.update(config.app_config)
    return app
