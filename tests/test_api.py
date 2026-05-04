import io
import pytest
from PIL import Image


def make_png_bytes(size=(100, 100), color=(255, 0, 0)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format="PNG")
    return buf.getvalue()


def store_image(client, url="http://example.com/test.png", client_name="test"):
    data = make_png_bytes()
    return client.post(
        "/images",
        data={"url": url, "client_name": client_name, "lookup_time": "2024-01-01T00:00:00"},
        files={"file": ("test.png", data, "image/png")},
    )


def test_store_new(client):
    resp = store_image(client)
    assert resp.status_code == 201
    body = resp.json()
    assert "content_hash" in body
    assert body["url"] == "http://example.com/test.png"


def test_store_duplicate(client):
    r1 = store_image(client)
    r2 = store_image(client)
    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r1.json()["content_hash"] == r2.json()["content_hash"]


def test_get_bytes(client):
    resp = store_image(client)
    h = resp.json()["content_hash"]
    r = client.get(f"/images/{h}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    assert len(r.content) > 0


def test_get_meta(client):
    resp = store_image(client)
    h = resp.json()["content_hash"]
    r = client.get(f"/images/meta/{h}")
    assert r.status_code == 200
    body = r.json()
    assert body["content_hash"] == h
    assert "id" not in body


def test_lookup_hit(client):
    url = "http://example.com/unique.png"
    store_image(client, url=url)
    r = client.get(f"/images/lookup?url={url}")
    assert r.status_code == 200
    assert r.json()["url"] == url


def test_lookup_miss(client):
    r = client.get("/images/lookup?url=http://example.com/nothere.png")
    assert r.status_code == 404


def test_search_match(client):
    store_image(client, url="http://example.com/images/cat.png")
    store_image(client, url="http://other.com/dog.png", client_name="other")
    r = client.get("/images/search?url_contains=example.com")
    assert r.status_code == 200
    results = r.json()
    assert len(results) >= 1
    assert all("example.com" in x["url"] for x in results)


def test_search_empty(client):
    r = client.get("/images/search?url_contains=zzznomatch")
    assert r.status_code == 200
    assert r.json() == []


def test_search_no_binary(client):
    store_image(client, url="http://example.com/img.png")
    r = client.get("/images/search?url_contains=example.com")
    assert r.status_code == 200
    for item in r.json():
        assert "file" not in item
        assert "data" not in item


def test_delete(client):
    resp = store_image(client)
    h = resp.json()["content_hash"]
    r = client.delete(f"/images/{h}")
    assert r.status_code == 204
    r2 = client.get(f"/images/{h}")
    assert r2.status_code == 404


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
