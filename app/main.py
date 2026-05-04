from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.database import get_engine
from app.models import Base
from app import metrics as m


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    m.init_metrics(settings.otel_service_name, settings.otel_exporter_otlp_endpoint)
    yield
    m.shutdown_metrics()


app = FastAPI(title="imgcache", lifespan=lifespan)

from app.routes.images import router
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def prometheus_metrics():
    from prometheus_client import CONTENT_TYPE_LATEST
    from app.metrics import get_metrics_output
    from fastapi.responses import Response
    return Response(get_metrics_output(), media_type=CONTENT_TYPE_LATEST)
