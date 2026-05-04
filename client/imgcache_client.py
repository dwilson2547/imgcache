import httpx
from datetime import datetime
from typing import Optional


class ImgCacheClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self._base, timeout=timeout)

    def store(self, url: str, file_bytes: bytes, client_name: str,
              lookup_time: Optional[datetime] = None, filename: Optional[str] = None) -> dict:
        data: dict = {"url": url, "client_name": client_name}
        if lookup_time is not None:
            data["lookup_time"] = lookup_time.isoformat() if isinstance(lookup_time, datetime) else lookup_time
        fname = filename or "image"
        resp = self._client.post(
            "/images",
            data=data,
            files={"file": (fname, file_bytes)},
        )
        resp.raise_for_status()
        return resp.json()

    def get_bytes(self, content_hash: str) -> bytes:
        resp = self._client.get(f"/images/{content_hash}")
        resp.raise_for_status()
        return resp.content

    def get_meta(self, content_hash: str) -> Optional[dict]:
        resp = self._client.get(f"/images/meta/{content_hash}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def lookup(self, url: str) -> Optional[dict]:
        resp = self._client.get("/images/lookup", params={"url": url})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def search(self, url_contains: str) -> list:
        resp = self._client.get("/images/search", params={"url_contains": url_contains})
        resp.raise_for_status()
        return resp.json()

    def similar(self, perceptual_hash: str, max_hamming_distance: int = 4) -> list:
        resp = self._client.get(
            "/images/similar",
            params={"perceptual_hash": perceptual_hash, "max_hamming_distance": max_hamming_distance},
        )
        resp.raise_for_status()
        return resp.json()

    def delete(self, content_hash: str) -> None:
        resp = self._client.delete(f"/images/{content_hash}")
        resp.raise_for_status()

    def health(self) -> dict:
        resp = self._client.get("/health")
        resp.raise_for_status()
        return resp.json()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.close()
