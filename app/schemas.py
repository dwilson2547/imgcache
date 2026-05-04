from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ImageEntryMeta(BaseModel):
    url: str
    content_hash: str
    content_type: str
    file_size_bytes: int
    original_filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    perceptual_hash: Optional[str] = None
    client_name: str
    lookup_time: datetime
    created_at: datetime

    class Config:
        from_attributes = True
