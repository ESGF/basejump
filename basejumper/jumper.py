import multiprocessing
import time
from mock.datastream import stream_file, file_metadata
import os


logfile = "/Users/fries2/basejumpd.log"


def poll_db():
    from db import Transfer, session
    while True:
        with session() as s:
            t = s.query(Transfer).filter(Transfer.progress < 100).first()
            if t is not None:
                transfer(t, s)
            else:
                time.sleep(60)


def transfer(t, s):
    log = open(logfile, "a")
    t.started = True
    log.write("Starting transfer of %s\n" % t.path)
    s.commit()
    
    # Collect the metadata
    meta = file_metadata(t.path)
    size = meta["size"]
    file_hash = meta["hash"]

    log.write("Metadata:\n")
    log.write("Size: %d\n" % size)
    log.write("Hash: %s\n" % file_hash)
    log.write("Key: %s\n" % meta["key"])

    cache_path = "/tmp/%s" % meta["key"]

    log.write("Cache File: %s\n" % cache_path)

    # Stream the file in
    with open(cache_path, "w+b") as f:
        for chunk in stream_file(t.path):
            f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
            written_size = os.fstat(f.fileno()).st_size
            t.progress = int(float(written_size) / size * 100)
            log.write("Progress: %d\n" % t.progress)
            log.flush()
            os.fsync(log.fileno())
            s.commit()
        t.progress = 100
        s.commit()
    log.write("All done with %s\n" % t.path)
    log.close()


def startd():
    new_process = multiprocessing.Process(target=poll_db, name="basejumperd")
    new_process.daemon = True
    new_process.start()
    return new_process
