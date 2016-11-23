from flask import Flask, request, jsonify, g, session, redirect, send_file, url_for, Response
from addons import querykeys
import datastream
import db
from models import Transfer, File, Notification
import security
from datetime import datetime, timedelta
from flask.ext.openid import OpenID
import access_control
from filecache import FileCache
import json
import os
from mailer import Mailer


app = Flask(__name__)
filecache = None
oid = OpenID(app)
mailer = None
database = None
db_session = None
login_exempt = ["main", "queue_job", "expose_path", "queued_jobs", "start_transfer", "update_transfer", "complete_transfer", "reset_transfer"]


@app.before_request
def lookup_current_user():
    g.user = None
    if "openid" in session:
        openid = session["openid"]
        g.user = openid
        g.user_email = session["email"]
    else:
        is_safe_route = request.endpoint in login_exempt
        if not is_safe_route and ("logging_in" not in session or session["logging_in"] is False):
            url = url_for("login", next=request.url)
            return redirect(url)


@app.route("/login", methods=["GET", "POST"])
@oid.loginhandler
def login():
    if g.user is not None:
        next_url = oid.get_next_url()
        if next_url.startswith(url_for("login")):
            return redirect(url_for("main"))
        else:
            redirect(next_url)
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


@app.route("/transfers")
def get_user_xfers():
    with db_session() as s:
        transfers = []
        for notif in s.query(Notification).filter(Notification.email == g.user_email).all()
            transfers.append({"file": notif.transfer.file.path, "progress": notif.transfer.progress, "started": notif.transfer.started})
    return jsonify(transfers)


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


@app.route("/expose/<group>", methods=["POST"])
def expose_path(group):
    form_keys = ["path", "size", "hash", "hash_function", "modified", "signature"]
    for key in form_keys:
        if key not in request.form:
            raise ValueError("Missing form value %s" % key)
    path = request.form["path"]
    signature = request.form["signature"]

    # Don't include signature
    d = {k: request.form[k] for k in form_keys[:-1]}

    if not security.check_json_sig(d, app.config["BASEJUMP_KEY"], signature):
        raise ValueError("Invalid signature provided.")

    key = security.sign_path(path, app.config["SECRET_KEY"])

    meta = request.form
    with db_session() as s:
        f = s.query(File).filter(File.key == key).all()
        if f:
            raise ValueError("This path is already exposed.")

        last_modified = datetime.fromtimestamp(int(meta["modified"]))
        f = File(path=path, group=group, key=key, size=meta["size"], checksum=meta["hash"], checksumType=meta["hash_function"], modified=last_modified)
        s.add(f)
        s.commit()
        url_path = f.queue_url()
    url = request.url_root + url_path
    return jsonify({"queue_url": url})


@app.route("/queue")
@querykeys
def queued_jobs(timestamp=None, signed_stamp=None):
    if None in (timestamp, signed_stamp):
        raise ValueError("No credentials provided.")
    if (datetime.now() -  datetime(1970, 1, 1)).total_seconds() - float(timestamp) > 30:
        raise ValueError("Timestamp too old.")
    if not security.hmac_compare(app.config["BASEJUMP_KEY"], timestamp, signed_stamp):
        raise ValueError("Invalid credentials.")

    with db_session() as s:
        transfers = s.query(Transfer).filter(Transfer.started == False)
        details = [{"id": t.id, "key": t.file.key, "path": t.file.path} for t in transfers.all()]
        return Response(json.dumps(details), mimetype="application/json")

@app.route("/transfers/<tid>/reset", methods=["POST"])
def reset_transfer(tid):
    if "signature" not in request.form:
        raise ValueError("No credentials provided.")
    signature = request.form["signature"]
    if not security.hmac_compare(app.config["BASEJUMP_KEY"], "/transfers/%s/reset" % (tid), signature):
        raise ValueError("Invalid credentials.")
    with db_session() as s:
        transfer = s.query(Transfer).filter(Transfer.id == tid and Transfer.started == True).first()
        if transfer is None:
            raise ValueError("No started transfer with id found.")
        transfer.started = False
        s.add(transfer)
        s.commit()
        return jsonify({"result": "success"})

@app.route("/transfers/<tid>/start", methods=["POST"])
def start_transfer(tid):
    if "signature" not in request.form:
        raise ValueError("No credentials provided.")
    signature = request.form["signature"]
    if not security.hmac_compare(app.config["BASEJUMP_KEY"], "/transfers/%s/start" % (tid), signature):
        raise ValueError("Invalid credentials.")
    with db_session() as s:
        transfer = s.query(Transfer).filter(Transfer.id == tid).first()
        if transfer is None:
            raise ValueError("No such transfer.")

        f = transfer.file
        if not filecache.make_space_for(f.size):
            response = jsonify({"result": "failure"})
            # "Entity Too Large" error
            response.status_code = 413
            response.headers["Retry-After"] = "24"
            return response
        transfer.started = True
        s.add(transfer)
        s.commit()
        return jsonify({"result": "success", "filepath": filecache.get_file_path(f.key)})


@app.route("/transfers/<tid>/progress", methods=["POST"])
def update_transfer(tid):
    progress, signature = request.form.get("progress", None), request.form.get("signature", None)
    if None in (progress, signature):
        raise ValueError("Need value for progress and signature.")
    if not security.hmac_compare(app.config["BASEJUMP_KEY"], progress, signature):
        raise ValueError("Invalid credentials.")
    try:
        progress = int(progress)
    except:
        raise ValueError("Invalid progress value.")
    with db_session() as s:
        transfer = s.query(Transfer).filter(Transfer.id == tid and Transfer.started == True).first()
        if transfer is None:
            raise ValueError("No such transfer.")
        transfer.progress = progress
        s.add(transfer)
        s.commit()
    return jsonify(result="success")


@app.route("/transfers/<tid>/complete", methods=["POST"])
def complete_transfer(tid):
    signature = request.form.get("signature", None)
    if signature is None:
        raise ValueError("Need value for signature.")
    if not security.hmac_compare(app.config["BASEJUMP_KEY"], "/transfers/%s/complete" % tid, signature):
        raise ValueError("Invalid credentials.")

    with db_session() as s:
        transfer = s.query(Transfer).filter(Transfer.id == tid and Transfer.started == True).first()
        if transfer is None:
            raise ValueError("No such transfer.")
        filepath = filecache.get_file_path(transfer.file.key)
        if not os.path.exists(filepath):
            raise ValueError("File not found.")
        transfer.progress = 100
        s.add(transfer)
        emails = []
        d = datetime.now()
        for subscriber in transfer.subscribers:
            emails.append(subscriber.email)
            subscriber.last_notified = d
            s.add(subscriber)
        message = """Your file transfer of {filename} is complete.\
 Please download it at {download_url} in the next week,\
 otherwise it may be deleted to make room.""".format(filename=transfer.file.file_name(),
                                                     download_url=url_for("download_file", key=transfer.file.key, _external=True))
        subject = "HPSS Transfer Complete"
        mailer.send_email(subject, message, emails)
        s.commit()


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
            if t.progress < 100:
                for sub in t.subscribers:
                    if sub.email == g.user_email:
                        break
                else:
                    notif = Notification(transfer_id=t.id, email=g.user_email)
                    s.add(notif)
                    s.commit()
            else:
                # Redirect to download URL
                return redirect(url_for("download_file", key=key, _external=True))
            break
        else:
            # Queue transfer in DB
            t = Transfer(file=f, progress=0)
            s.add(t)
            s.commit()
            notif = Notification(transfer_id=t.id, email=g.user_email)
            s.add(notif)
            s.commit()

    progress_url = url_for("job_progress", key=key, _external=True)
    return redirect(progress_url)


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
            #return send_file(filecache.get_file_path(transfer.file.key), as_attachment=True, attachment_filename=transfer.file.file_name())

        raise ValueError("File not ready for download.")

@app.errorhandler(404)
def page_not_found(err):
    real_url = url_for("login")
    return "This route does not exist {}; are you looking for {}?".format(request.url, real_url), 404


def configure(config):
    global database
    database = db.DB(config.db_config)
    global db_session
    db_session = database.session
    app.config.update(config.app_config)
    access_control.configure(config.app_config)
    global filecache
    filecache = FileCache(config.cache_config, database.Session())
    global mailer
    mailer = Mailer(config.smtp_config["server"], config.smtp_config["from_address"])
    return app
