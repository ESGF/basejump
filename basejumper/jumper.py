import multiprocessing
import time
from mock.datastream import stream_file, file_metadata
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
    
    # Collect the metadata
    meta = file_metadata(t.path)
    size = meta["size"]
    file_hash = meta["hash"]

    log.info("Metadata:")
    log.info("Size: %d" % size)
    log.info("Hash: %s" % file_hash)
    log.info("Key: %s" % meta["key"])

    cache_path = "/tmp/%s" % meta["key"]

    log.info("Cache File: %s" % cache_path)

    # Stream the file in
    with open(cache_path, "w+b") as f:
        for chunk in stream_file(t.path):
            f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
            written_size = os.fstat(f.fileno()).st_size
            t.progress = int(float(written_size) / size * 100)
            log.info("Progress: %d" % t.progress)
            s.commit()
        t.progress = 100
        s.commit()
    log.info("All done with %s" % t.path)


def startd(config):
    conf = {"db":config.db_config, "log": config.log_config}
    new_process = multiprocessing.Process(target=poll_db, name="basejumperd", args=[conf])
    new_process.daemon = True
    new_process.start()
    return new_process
