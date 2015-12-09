import sqlalchemy
from sqlalchemy.orm import sessionmaker
from models import Base
import os.path
from contextlib import contextmanager


class DB(object):
    def __init__(self, config):
        db_type = config["type"]
        db_url = config["url"]
        url = ":///".join((db_type, db_url))
        self.engine = sqlalchemy.create_engine(url)
        self.Session = sessionmaker(bind=self.engine)

    def initdb(self):
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self):
        s = self.Session()
        try:
            yield s
            s.commit()
        except:
            s.rollback()
            raise
        finally:
            s.close()
