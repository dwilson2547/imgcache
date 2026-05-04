from app.storage.base import BaseStorage

_storage = None

def get_storage() -> BaseStorage:
    global _storage
    if _storage is None:
        from app.config import settings
        if settings.storage_backend == "s3":
            from app.storage.s3 import S3Storage
            _storage = S3Storage(
                bucket=settings.s3_bucket,
                endpoint_url=settings.s3_endpoint_url or None,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
            )
        else:
            from app.storage.local import LocalStorage
            _storage = LocalStorage(settings.local_storage_path)
    return _storage

def override_storage(instance: BaseStorage) -> None:
    global _storage
    _storage = instance

def reset_storage() -> None:
    global _storage
    _storage = None
