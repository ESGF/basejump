from flask import Flask, request, jsonify, g, session, redirect, send_file, url_for
from addons import querykeys
import datastream
import db
from models import Transfer, File, Notification
import security
from datetime import datetime
from flask.ext.openid import OpenID
import access_control
from filecache import FileCache
import os


app = Flask(__name__)
filecache = None
oid = OpenID(app)

database = None
db_session = None
login_exempt = ["login", "metadata", "expose"]


@app.before_request
def lookup_current_user():
    g.user = None
    if "openid" in session:
        openid = session["openid"]
        g.user = openid
        g.user_email = session["email"]
    else:
        path_elements = os.path.split(request.path)
        if app.config.get("APPLICATION_ROOT", None):
            path_elements = path_elements[1:]
        is_safe_route = path_elements[0] in login_exempt
        if not is_safe_route and ("logging_in" not in session or session["logging_in"]is False):
            url = url_for("login", next=request.path)
            return redirect(url)


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
        err = session.pop("openid_error")
        return """
        <div style="color: red;">Error: %s</div>
        <form action="%s" method="POST">
            OpenID:
            <input type="text" name="openid" />
            <input type="submit" value="Log In" />
        </form>""" % (err, url_for("login"))
    return """ 
            <form action="%s" method="POST">
                OpenID:
                <input type="text" name="openid" />
                <input type="submit" value="Log In" />
            </form>""" % (url_for("login"),)


@oid.errorhandler
def on_error(message):
    session.pop("logging_in", None)
    url = url_for("login", next=oid.get_next_url())
    return redirect(url)


@oid.after_login
def logged_in(resp):
    session["openid"] = resp.identity_url
    session["email"] = resp.email
    session.pop("logging_in", None)
    session.pop("openid_error", None)
    return redirect(oid.get_next_url())


@app.route('/logout')
def logout_user():
    session.pop("openid", None)
    url = url_for("login")
    return redirect(url)


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

        f = s.query(File).filter(File.key == key and File.group == group).all()
        if not f:
            raise ValueError("No file matching key/group exposed.")

        f = f[0]

        # Verify Permissions
        if access_control.check_access(g.user) is False:
            # Should redirect to the registration URL for the relevant group...
            raise ValueError("User does not have access to the requested file.")

        # Check if already queued
        for t in s.query(Transfer).filter(Transfer.file == f):
            for sub in t.subscribers:
                if sub.email == g.user_email:
                    break
            else:
                notif = Notification(transfer_id=t.id, email=g.user_email)
                s.add(notif)
                s.commit()
            # Check if there's an existing transfer for this file
            break
        else:
            # Queue transfer in DB
            t = Transfer(file=f, progress=0)
            s.add(t)
            s.commit()
            notif = Notification(transfer_id=t.id, email=g.user_email)
            s.add(notif)
            s.commit()

    return jsonify({"progress": "/progress/%s" % key})


@app.route("/download/<key>")
def download_file(key):
    """
    /download/<file_key> ->
        Authorizes download through ESGF
        Checks if the user has asked for this file, and removes them from the list of users
        Transfers file
    """
    if key is None:
        raise ValueError("No key provided")

    with db_session() as s:
        f = s.query(File).filter(File.key == key)
        if not f:
            raise ValueError("File not found.")

        f = f[0]
        if not access_control.check_access(g.user, url= "/%s/%s" % (f.group, f.key)):
            raise ValueError("File not found.")

        for transfer in f.transfers:
            if transfer.progress != 100:
                continue

            # Check if the user is in the notification list
            for notif in transfer.subscribers:
                if notif.email == g.user_email:
                    # TODO: Only delete the user from the notification list if the download is successful.
                    s.delete(notif)
                    break
            s.commit()
            return send_file(filecache.get_file_path(transfer.file.key), as_attachment=True, attachment_filename=transfer.file.file_name())

        raise ValueError("File not ready for download.")


def configure(config):
    global database
    database = db.DB(config.db_config)
    global db_session
    db_session = database.session
    app.config.update(config.app_config)
    print "PUB SECRET KEY", app.config["PUBLISHER_SECRET_KEY"]
    access_control.configure(config.app_config)
    global filecache
    filecache = FileCache(config.cache_config, database.Session())
    return app
