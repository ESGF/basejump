from flask import Flask, request, jsonify, g, session, redirect
from addons import querykeys
import datastream
import db
from models import Transfer, File
import security
from datetime import datetime
from flask.ext.openid import OpenID
import urllib
import access_control

app = Flask(__name__)

oid = OpenID(app)

database = None
db_session = None
login_exempt = ["/login", "/metadata", "/expose"]


@app.before_request
def lookup_current_user():
    g.user = None
    if "openid" in session:
        openid = session["openid"]
        g.user = openid
    else:
        # Requires
        if all([not request.path.startswith(p) for p in login_exempt]) and ("logging_in" not in session or session["logging_in"]is False):
            return redirect("/login?" + urllib.urlencode({"next": request.path}))


@app.route("/login", methods=["GET", "POST"])
@oid.loginhandler
def login():
    if g.user is not None:
        return redirect(oid.get_next_url())
    if request.method == "POST":
        openid = request.form.get("openid")
        if openid:
            session["logging_in"] = True
            return oid.try_login(openid, ask_for=["email"])
    if "openid_error" in session:
        return """
        <div style="color: red;">Error: %s</div>
        <form action="/login" method="POST">
            OpenID:
            <input type="text" name="openid" />
            <input type="submit" value="Log In" />
        </form>"""
    return """
            <form action="/login" method="POST">
                OpenID:
                <input type="text" name="openid" />
                <input type="submit" value="Log In" />
            </form>"""

@oid.errorhandler
def on_error(message):
    del session["logging_in"]
    return redirect("/login?" + urllib.urlencode({"next": oid.get_next_url()}))


@oid.after_login
def logged_in(resp):
    session["openid"] = resp.identity_url
    session.pop("logging_in", None)
    return redirect(oid.get_next_url())


@app.route('/logout')
def logout_user():
    session.pop("openid", None)
    return redirect("/login")


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
    with db_session() as s:
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


@app.route("/expose/<group>", methods=["POST"])
def expose_path(group):
    if "path" not in request.form or "key" not in request.form:
        raise ValueError("Path and Key are required to expose a path")
    path, key = request.form["path"], request.form["key"]
    test_key = datastream.file_key(path)
    matches = security.constant_time_compare(test_key, key)

    if not matches:
        raise ValueError("Key is invalid for provided path")

    meta = datastream.file_metadata(path)
    with db_session() as s:
        f = s.query(File).filter(File.key == key).all()
        if f:
            raise ValueError("This path is already exposed.")

        last_modified = datetime.fromtimestamp(meta["modified"])
        f = File(path=path, group=group, key=key, size=meta["size"], checksum=meta["hash"], checksumType=meta["hash_function"], modified=last_modified)
        s.add(f)
        s.commit()
        url_path = f.queue_url()
    url = request.url_root + url_path
    return jsonify({"queue_url": url})


@app.route("/queue/<group>/<key>")
def queue_job(group, key):
    """
    /queue/<group>/<file_key> ->
        Authenticate Session w/ESGF
        Verify Permissions w/ESGF
        Check File Exists
        Queue in DB
    """
    if key is None:
        raise ValueError("No key provided.")

    with db_session() as s:

        f = s.query(File).filter(File.key == key)
        if not f:
            raise ValueError("No file matching key exposed.")

        f = f[0]

        # Verify Permissions
        if access_control.check_access(g.user) is False:
            # Should redirect to the registration URL for the relevant group...
            raise ValueError("User does not have access to the requested file.")

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
    global db_session
    db_session = database.session
    app.config.update(config.app_config)
    access_control.configure(config.app_config)

    return app
