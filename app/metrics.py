from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import generate_latest, REGISTRY, CONTENT_TYPE_LATEST

_meter_provider = None
_meter = None
_prometheus_reader = None
# Keep for backward-compat (conftest resets this name)
_prometheus_registry = None

store_counter = None
lookup_counter = None
image_bytes_histogram = None
perceptual_hash_counter = None
similar_search_counter = None


def _unregister_prometheus_reader():
    """Unregister the OTel collector from the global Prometheus registry."""
    global _prometheus_reader
    if _prometheus_reader is not None:
        try:
            REGISTRY.unregister(_prometheus_reader._collector)
        except Exception:
            pass
        _prometheus_reader = None


def init_metrics(service_name: str, otlp_endpoint: str):
    global _meter_provider, _meter, _prometheus_reader
    global store_counter, lookup_counter, image_bytes_histogram
    global perceptual_hash_counter, similar_search_counter

    _unregister_prometheus_reader()

    prometheus_reader = PrometheusMetricReader()
    _prometheus_reader = prometheus_reader

    otlp_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
    otlp_reader = PeriodicExportingMetricReader(otlp_exporter)

    _meter_provider = MeterProvider(metric_readers=[otlp_reader, prometheus_reader])
    # Use the provider directly instead of the global API to allow re-initialisation in tests
    _meter = _meter_provider.get_meter(service_name)

    store_counter = _meter.create_counter("imgcache.store.total")
    lookup_counter = _meter.create_counter("imgcache.lookup.total")
    image_bytes_histogram = _meter.create_histogram("imgcache.image_bytes")
    perceptual_hash_counter = _meter.create_counter("imgcache.perceptual_hash.computed")
    similar_search_counter = _meter.create_counter("imgcache.similar_search.total")


def get_metrics_output() -> bytes:
    if _prometheus_reader is None:
        return b""
    return generate_latest(REGISTRY)


def shutdown_metrics():
    global _meter_provider
    if _meter_provider:
        _meter_provider.shutdown()
        _meter_provider = None
    _unregister_prometheus_reader()
