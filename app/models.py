from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase
import datetime

class Base(DeclarativeBase):
    pass

class ImageEntry(Base):
    __tablename__ = "image_entries"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    content_hash = Column(String(64), unique=True, index=True)
    content_type = Column(String)
    file_size_bytes = Column(Integer)
    original_filename = Column(String, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    perceptual_hash = Column(String(16), nullable=True)
    client_name = Column(String)
    lookup_time = Column(DateTime)
    created_at = Column(DateTime(timezone=True))
