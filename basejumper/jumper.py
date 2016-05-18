import multiprocessing
import time
import datastream
import os
import logging
import datetime
from filecache import FileCache
from mailer import Mailer


filecache = None
mailer = None


def get_log():
    return logging.getLogger("basejumpd")


def poll_db(conf):
    from db import DB
    from models import Transfer
    global filecache
    global mailer

    logging.basicConfig(**conf["log"])

    datastream.initclient(**conf["base"])

    smtp_server = conf["smtp"]["server"]
    fromaddr = conf["smtp"]["from_address"]
    mailer = Mailer(smtp_server, fromaddr)
    database = DB(conf["db"])
    filecache = FileCache(conf["cache"], database.Session())

    while True:
        with database.session() as s:
            log = get_log()
            log.info("Checking for unfinished transfers")
            # At some point will need to tidy this selection process up to see if a transfer is active or not
            transfers = s.query(Transfer).filter(Transfer.progress < 100).all()
            for t in transfers:
                log.info("Found transfer of %s" % t.file.key)
                if t.progress > 0:
                    log.info("Restarting transfer of %s" % t.file.key)
                    transfer(t, s)
                    break
                else:
                    log.info("Checking if there's enough space for %s" % t.file.key)
                    if filecache.make_space_for(t.file.size):
                        transfer(t, s)
                        break
                    else:
                        log.info("Wasn't able to free up space for %s" % t.file.key)
            log.info("Resting for a minute")
            time.sleep(60)
            log.info("Ready to take another look!")


def transfer(t, s):
    log = get_log()
    t.started = True
    f = t.file
    log.info("Starting transfer of %s" % f.path)
    s.commit()

    cache_path = os.path.join(filecache.path, f.key)
    log.info("Cache File: %s" % cache_path)

    for percent in datastream.stream_file(f.path, cache_path):
        log.info("Transfer: %d%%" % percent)
        t.progress = percent
        s.commit()

    emails = []
    d = datetime.datetime.now()
    for subscriber in t.subscribers:
        emails.append(subscriber.email)
        subscriber.last_notified = d
        s.add(subscriber)
    message = """Your file transfer of {filename} is complete.\
 Please download it at {download_url} in the next week,\
 otherwise it may be deleted to make room.""".format(filename=f.file_name(),
                                                     download_url="http://pcmdi11.llnl.gov/basej/download/{key}".format(key=f.key))
    subject = "HPSS Transfer Complete"
    mailer.send_email(subject, message, emails)
    s.commit()

    log.info("All done with %s" % f.path)


def startd(config, fork=True):
    conf = {"daemon": config.daemon_config,
            "smtp": config.smtp_config,
            "db": config.db_config,
            "log": config.log_config,
            "cache": config.cache_config,
            "base": config.base_config
            }
    if fork:
        new_process = multiprocessing.Process(target=poll_db, name="basejumperd", args=[conf])
        new_process.daemon = True
        new_process.start()
        return new_process
    else:
        poll_db(conf)
