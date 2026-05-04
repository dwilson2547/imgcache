import hashlib
import os
import urllib.parse
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app import metrics as m
from app.database import get_session
from app.models import ImageEntry
from app.perceptual import compute_dhash
from app.schemas import ImageEntryMeta
from app.storage import get_storage

router = APIRouter()


def _content_type_from_bytes(data: bytes, filename: str = "") -> str:
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        mapping = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "GIF": "image/gif",
            "WEBP": "image/webp",
            "BMP": "image/bmp",
            "TIFF": "image/tiff",
            "ICO": "image/x-icon",
        }
        if fmt in mapping:
            return mapping[fmt]
    except Exception:
        pass
    snippet = data[:512]
    try:
        text = snippet.decode("utf-8", errors="ignore")
        if "<svg" in text or "<?xml" in text.lower():
            return "image/svg+xml"
    except Exception:
        pass
    return "application/octet-stream"


def _get_dimensions(data: bytes):
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data))
        img.load()
        return img.size
    except Exception:
        return None, None


def _original_filename(url: str) -> Optional[str]:
    try:
        path = urllib.parse.urlparse(url).path
        name = os.path.basename(path)
        name = name.split("?")[0]
        return name if name else None
    except Exception:
        return None


@router.get("/images/meta/{content_hash}", response_model=ImageEntryMeta)
def get_meta(content_hash: str, db: Session = Depends(get_session)):
    entry = db.query(ImageEntry).filter(ImageEntry.content_hash == content_hash).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    return entry


@router.get("/images/lookup", response_model=ImageEntryMeta)
def lookup(url: str, db: Session = Depends(get_session)):
    entry = (
        db.query(ImageEntry)
        .filter(ImageEntry.url == url)
        .order_by(ImageEntry.created_at.desc())
        .first()
    )
    if not entry:
        if m.lookup_counter:
            m.lookup_counter.add(1, {"result": "miss"})
        raise HTTPException(status_code=404, detail="Not found")
    if m.lookup_counter:
        m.lookup_counter.add(1, {"result": "hit"})
    return entry


@router.get("/images/search", response_model=List[ImageEntryMeta])
def search(url_contains: str, db: Session = Depends(get_session)):
    entries = db.query(ImageEntry).filter(ImageEntry.url.contains(url_contains)).all()
    return entries


@router.get("/images/similar", response_model=List[ImageEntryMeta])
def similar(
    perceptual_hash: str,
    max_hamming_distance: int = 4,
    db: Session = Depends(get_session),
):
    if m.similar_search_counter:
        m.similar_search_counter.add(1)
    query_int = int(perceptual_hash, 16)
    results = []
    entries = db.query(ImageEntry).filter(ImageEntry.perceptual_hash != None).all()
    for entry in entries:
        try:
            dist = bin(query_int ^ int(entry.perceptual_hash, 16)).count("1")
            if dist <= max_hamming_distance:
                results.append(entry)
        except Exception:
            continue
    return results


@router.get("/images/{content_hash}")
def get_image(content_hash: str, db: Session = Depends(get_session)):
    entry = db.query(ImageEntry).filter(ImageEntry.content_hash == content_hash).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    storage = get_storage()
    data = storage.read(content_hash)
    return Response(content=data, media_type=entry.content_type)


@router.delete("/images/{content_hash}", status_code=204)
def delete_image(content_hash: str, db: Session = Depends(get_session)):
    entry = db.query(ImageEntry).filter(ImageEntry.content_hash == content_hash).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    storage = get_storage()
    storage.delete(content_hash)
    db.delete(entry)
    db.commit()
    return None


@router.post("/images", response_model=ImageEntryMeta)
async def store_image(
    file: UploadFile = File(...),
    url: str = Form(...),
    client_name: str = Form(...),
    lookup_time: Optional[str] = Form(None),
    db: Session = Depends(get_session),
):
    data = await file.read()
    content_hash = hashlib.blake2b(data, digest_size=32).hexdigest()

    existing = db.query(ImageEntry).filter(ImageEntry.content_hash == content_hash).first()
    if existing:
        if m.store_counter:
            m.store_counter.add(1, {"result": "duplicate"})
        from fastapi.responses import JSONResponse
        from fastapi.encoders import jsonable_encoder
        meta = ImageEntryMeta.model_validate(existing)
        return JSONResponse(content=jsonable_encoder(meta), status_code=200)

    content_type = _content_type_from_bytes(data, file.filename or "")
    width, height = _get_dimensions(data)
    phash = compute_dhash(data)

    if phash:
        if m.perceptual_hash_counter:
            m.perceptual_hash_counter.add(1, {"result": "ok"})
    else:
        if m.perceptual_hash_counter:
            m.perceptual_hash_counter.add(1, {"result": "failed"})

    if m.image_bytes_histogram:
        m.image_bytes_histogram.record(len(data))

    lookup_dt = datetime.fromisoformat(lookup_time) if lookup_time else datetime.now(tz=timezone.utc)
    created_at = datetime.now(tz=timezone.utc)
    orig_filename = _original_filename(url)

    entry = ImageEntry(
        url=url,
        content_hash=content_hash,
        content_type=content_type,
        file_size_bytes=len(data),
        original_filename=orig_filename,
        width=width,
        height=height,
        perceptual_hash=phash,
        client_name=client_name,
        lookup_time=lookup_dt,
        created_at=created_at,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    storage = get_storage()
    storage.write(content_hash, data)

    if m.store_counter:
        m.store_counter.add(1, {"result": "created"})

    from fastapi.responses import JSONResponse
    from fastapi.encoders import jsonable_encoder
    meta = ImageEntryMeta.model_validate(entry)
    return JSONResponse(content=jsonable_encoder(meta), status_code=201)
