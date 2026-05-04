from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///./imgcache.db"
    storage_backend: str = "local"
    local_storage_path: str = "./data"
    s3_bucket: str = "imgcache"
    s3_endpoint_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "imgcache"

    class Config:
        env_file = ".env"

settings = Settings()
