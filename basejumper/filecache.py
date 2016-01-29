from models import Transfer, File
import os
import logging


logger = logging.getLogger("filecache")


class FileCache(object):
    def __init__(self, config, dbsession):
        self.path = config.get("path", "/data/basejump")
        self.max_size = config.get("size", 1024 ** 3)
        self.guarantee = config.get("guarantee", 7 * 24 * 60 * 60)
        self.session = dbsession

    def cache_size(self):
        size = 0

        # Calculate the size of the files in the cache
        for filename in os.listdir(self.path):
            # We don't want to look at the size on disk, but instead at the HPSS reported size
            # That way any transfers that are in process are accounted for
            files = self.session.query(File).filter(File.key == filename).all()
            if not files:
                # There's a file not managed by BASEJumper in the cache directory
                # Let's log the incident, get the file size, and account for that.
                logger.error("File %s found in cache directory, not managed by BASEJumper." % filename)
                stat = os.stat(os.path.join(self.path, filename))
                size += stat.st_size
                continue
            file_info = files[0]
            size += file_info.size

        return size

    def can_store(self, filesize):
        return filesize + self.cache_size() <= self.max_size

    def make_space_for(self, size):
        if size > self.max_size:
            # Log and return False
            logger.error("Asked to clear more space than allocated to cache.")
            return False

        size -= self.max_size - self.cache_size()

        if size <= 0:
            logger.info("Enough space available")
            return True

        to_delete = []

        # Grab list of files eligible for deletion, sorted by least recently accessed
        transfers = self.session.query(Transfer).filter(Transfer.progress == 100).order_by(Transfer.last_downloaded.desc())
        for t in transfers:
            if not t.downloaded():
                continue
            to_delete.append(t)
            size -= t.file.size
            if size <= 0:
                break

        for transfer in to_delete:
            transfer.delete()
            self.session.commit()
            os.remove(os.path.join(self.path, transfer.file.key))

        return size <= 0

    def get_file_path(self, key):
        if not os.path.exists(os.path.join(self.path, key)):
            raise ValueError("No file matching %s found." % key)

        files = self.session.query(File).filter(File.key == key)
        if not files:
            raise ValueError("No file matching %s found." % key)

        f = files[0]
        for transfer in f.transfers:
            if transfer.progress != 100:
                continue
            return os.path.join(self.path, key)

        raise ValueError("No file matching %s found." % key)
