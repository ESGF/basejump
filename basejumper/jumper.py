import multiprocessing
import time
import datastream
import os
import logging
import requests
import datetime
import security
import subprocess

secret = None
frontend_url = None
cache_path = None
transfer_cmd = None
verify = True

def get_log():
    return logging.getLogger("basejumpd")


def get_transfers():
    stamp = str((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds())
    transfer_response = requests.get(frontend_url + "/queue?timestamp={}&signed_stamp={}".format(stamp, security.sign_path(stamp, secret)), verify=verify)
    logging.debug("get_transfers: " + transfer_response.url)
    if transfer_response.status_code > 299:
        raise ValueError("Unable to retrieve transfers:" + transfer_response.text)
    return transfer_response.json()


def start_transfer(tid):
    url_path = "/transfers/{tid}/start".format(tid=tid)
    signature = security.sign_path(url_path, secret)
    start_response = requests.post(frontend_url + url_path, data={"signature": signature}, verify=verify)
    logging.debug("start_transfer: " + start_response.url)
    if start_response.status_code > 299:
        raise ValueError("Unable to start transfer:" + start_response.text)
    return start_response.json()["filepath"]


def update_progress(tid, progress):
    url_path = "/transfers/{tid}/progress".format(tid=tid)
    signature = security.sign_path(str(progress), secret)
    prog_response = requests.post(frontend_url + url_path, data={"progress": progress, "signature": signature}, verify=verify)
    logging.debug("update_progress: " + prog_response.url)
    if prog_response.status_code > 299:
        raise ValueError("Unable to update transfer progress:" + prog_response.text)


def reset_transfer(tid):
    url_path = "/transfers/{tid}/reset".format(tid=tid)
    signature = security.sign_path(url_path, secret)
    reset_response = requests.post(frontend_url + url_path, data={"signature": signature}, verify=verify)
    logging.debug("reset_transfer: " + reset_response.url)
    if reset_response.status_code > 299:
        raise ValueError("Unable to reset transfer progress. This transfer is now orphaned :(\n" + reset_response.text)


def complete_transfer(tid):
    url_path = "/transfers/{tid}/complete".format(tid=tid)
    signature = security.sign_path(url_path, secret)
    complete_response = requests.post(frontend_url + url_path, data={"signature": signature}, verify=verify)
    logging.debug("complete_transfer: " + complete_response.url)
    if complete_response.status_code > 299:
        raise ValueError("Unable to complete transfer:" + complete_response.text)


def poll_db(conf):
    global secret
    global frontend_url
    global cache_path
    global transfer_cmd
    global verify

    logging.basicConfig(**conf["log"])

    datastream.initclient(**conf["base"])
    frontend_url = conf["daemon"]["BASEJUMP_FRONTEND_URL"]
    secret = conf["daemon"]["BASEJUMP_KEY"]
    cache_path = conf["daemon"]["CACHE_DIR"]
    # An executable command that takes a "source path" and a "target path" to transfer a file
    transfer_cmd = conf["daemon"]["TRANSFER_CMD"]
    verify = conf["daemon"].get("SSL_VERIFY", True)

    if not os.path.exists(cache_path):
        os.mkdirs(cache_path)
    log = get_log()
    while True:
        try:
            transfers = get_transfers()

            for xfer in transfers:
                path = xfer["path"]
                # At some point will need to tidy this selection process up to see if a transfer is active or not
                log.info("Found transfer of %s" % path)
                if transfer(xfer):
                    log.info("Completed transfer of %s" % path)
                else:
                    log.info("Unable to transfer %s; will try later." % path)
                    reset_transfer(xfer["id"])

        except Exception as e:
            log.error("Unable to retrieve transfers.")
            log.exception(e)
        log.info("Resting for a minute")
        time.sleep(60)
        log.info("Ready to take another look!")


def transfer(xfer):
    log = get_log()
    path = xfer["path"]
    key = xfer["key"]
    tid = xfer["id"]

    log.info("Starting transfer of %s" % path)
    try:
        target_path = start_transfer(tid)
    except ValueError as e:
        log.exception(e)
        return False

    file_cache = os.path.join(cache_path, key)
    log.info("Cache File: %s" % file_cache)

    try:
        for percent in datastream.stream_file(path, file_cache):
            log.info("Transfer: %d%%" % percent)
            update_progress(tid, percent)
    except Exception as e:
        log.exception(e)
        return False

    try:
        log.debug(" ".join([str(s) for s in (transfer_cmd, file_cache, target_path)]))
        subprocess.call([transfer_cmd, file_cache, target_path])
    except Exception as e:
        log.exception(e)
        return False

    try:
        complete_transfer(tid)
    except Exception as e:
        log.exception(e)
        return False

    os.remove(file_cache)
    log.info("All done with %s" % path)
    return True


def startd(config, fork=True):
    conf = {"daemon": config.daemon_config,
            "log": config.log_config,
            "base": config.base_config
            }
    if fork:
        new_process = multiprocessing.Process(target=poll_db, name="basejumperd", args=[conf])
        new_process.daemon = True
        new_process.start()
        return new_process
    else:
        poll_db(conf)
