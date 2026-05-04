import io
import pytest
from PIL import Image


def make_png():
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200


def test_store_counter_in_metrics(client):
    data = make_png()
    client.post(
        "/images",
        data={"url": "http://m.com/1.png", "client_name": "mc", "lookup_time": "2024-01-01T00:00:00"},
        files={"file": ("1.png", data, "image/png")},
    )
    r = client.get("/metrics")
    assert "imgcache" in r.text


def test_lookup_counter_in_metrics(client):
    client.get("/images/lookup?url=http://m.com/nothere.png")
    r = client.get("/metrics")
    assert r.status_code == 200


def test_similar_search_counter(client):
    client.get("/images/similar?perceptual_hash=0000000000000000")
    r = client.get("/metrics")
    assert r.status_code == 200
