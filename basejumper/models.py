from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from urllib import urlencode

Base = declarative_base()


class Transfer(Base):
    """
    Transfer represents a file transfer

    Tracks progress and provides a task list for the daemon to start
    transfers.
    """

    __tablename__ = "transfer"

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("hpss_file.id"))
    file = relationship("File")
    progress = Column(Integer)
    started = Column(Boolean, default=False)


class File(Base):
    """
    File represents a file on HPSS that is exposed
    """
    __tablename__ = "hpss_file"

    id = Column(Integer, primary_key=True)
    key = Column(String)
    path = Column(String)
    group = Column(String)
    modified = Column(DateTime)
    size = Column(Integer)
    checksum = Column(String)
    checksumType = Column(Enum("sha256", "md5", name="checksum_types"))

    def queue_url(self):
        return "/queue" + urlencode({"key": self.key})
