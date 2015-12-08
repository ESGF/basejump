import sqlalchemy

# TODO: Use configuration to determine URL
db_type = "sqlite"
db_url = "/Users/fries2/basejump.db"

url = ":///".join((db_type, db_url))
engine = sqlalchemy.create_engine(url)

from models import Base

import os.path
if not os.path.exists(db_url):
    Base.metadata.create_all(engine)

# Provide handy objects in the namespace
from models import Transfer
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)
session = Session()
