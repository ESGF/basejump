from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
import os.path


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
    last_downloaded = Column(DateTime)
    subscribers = relationship("Notification", back_populates="transfer")

    def downloaded(self):
        return len(self.subscribers) == 0


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
    transfers = relationship(Transfer, back_populates="file")

    def file_name(self):
        return os.path.basename(self.path)

    def queue_url(self):
        return "/queue/" + self.group + "/" + self.key


class Notification(Base):
    """
    Notifications represents email address to notify when a transfer completes
    """
    __tablename__ = "notification"

    id = Column(Integer, primary_key=True)
    transfer_id = Column(Integer, ForeignKey("transfer.id"))
    transfer = relationship("Transfer")
    email = Column(String)
    last_notified = Column(DateTime)
