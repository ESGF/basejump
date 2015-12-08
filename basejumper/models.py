from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean

Base = declarative_base()


class Transfer(Base):
    """
    Transfer represents a file transfer

    Tracks progress and provides a task list for the daemon to start
    transfers.
    """

    __tablename__ = "transfer"

    id = Column(Integer, primary_key=True)
    key = Column(String)
    path = Column(String)
    progress = Column(Integer)
    started = Column(Boolean, default=False)
