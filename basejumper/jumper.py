import multiprocessing
import time
import datastream
import os
import logging
import datetime

logfile = "/Users/fries2/basejumpd.log"


def get_log():
    return logging.getLogger("basejumpd")


def poll_db(conf):
    from db import DB
    from models import Transfer
    database = DB(conf["db"])
    logging.basicConfig(**conf["log"])

    while True:
        with database.session() as s:
            log = get_log()
            log.info("Checking for unfinished transfers")
            t = s.query(Transfer).filter(Transfer.progress < 100).first()
            if t is not None:
                log.info("Found transfer; restarting.")
                transfer(t, s)
            else:
                time.sleep(60)


def transfer(t, s):
    log = get_log()
    t.started = True
    log.info("Starting transfer of %s" % t.path)
    s.commit()

    # TODO: Extract this to a config value
    cache_path = "/tmp/%s" % t.key
    log.info("Cache File: %s" % cache_path)

    for percent in datastream.stream_file(t.path, cache_path):
        log.info("Transfer: %d%%" % percent)
        t.progress = percent
        s.commit()

    log.info("All done with %s" % t.path)


def startd(config):
    conf = {"db":config.db_config, "log": config.log_config}
    new_process = multiprocessing.Process(target=poll_db, name="basejumperd", args=[conf])
    new_process.daemon = True
    new_process.start()
    return new_process
