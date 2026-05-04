import os
import pytest
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Set env vars BEFORE importing app
os.environ["STORAGE_BACKEND"] = "local"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

_tmpdir = tempfile.mkdtemp()
os.environ["LOCAL_STORAGE_PATH"] = _tmpdir

from app.models import Base
from app.database import override_engine
from app.storage import override_storage, reset_storage
from app.storage.local import LocalStorage


@pytest.fixture
def app(tmp_path):
    # Reset metrics state to avoid duplicate registration errors
    import app.metrics as m_module
    m_module._unregister_prometheus_reader()
    m_module._meter_provider = None
    m_module._meter = None
    m_module._prometheus_registry = None
    m_module.store_counter = None
    m_module.lookup_counter = None
    m_module.image_bytes_histogram = None
    m_module.perceptual_hash_counter = None
    m_module.similar_search_counter = None

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    override_engine(engine)

    storage = LocalStorage(str(tmp_path / "storage"))
    override_storage(storage)

    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def minio_container():
    try:
        from testcontainers.minio import MinioContainer
        container = MinioContainer()
        container.start()
        yield container
        container.stop()
    except Exception:
        pytest.skip("Docker not available")


@pytest.fixture
def s3_app(minio_container, tmp_path):
    from testcontainers.minio import MinioContainer
    host = minio_container.get_container_host_ip()
    port = minio_container.get_exposed_port(9000)
    endpoint = f"http://{host}:{port}"

    os.environ["STORAGE_BACKEND"] = "s3"
    os.environ["S3_BUCKET"] = "test-imgcache"
    os.environ["S3_ENDPOINT_URL"] = endpoint
    os.environ["AWS_ACCESS_KEY_ID"] = "minioadmin"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "minioadmin"

    from app.storage.s3 import S3Storage
    from app.storage import override_storage
    storage = S3Storage(
        bucket="test-imgcache",
        endpoint_url=endpoint,
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
    )
    override_storage(storage)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    from app.database import override_engine
    override_engine(engine)

    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture
def s3_client(s3_app):
    with TestClient(s3_app) as c:
        yield c
