"""Prometheus metrics of the prediction service."""
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

REGISTRY = CollectorRegistry()

HTTP_REQUESTS = Counter("netanomaly_http_requests_total", "HTTP requests", ["method", "path", "status"], registry=REGISTRY)
HTTP_LATENCY = Histogram("netanomaly_http_request_duration_seconds", "HTTP request duration", ["path"], registry=REGISTRY,
                         buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0))
PREDICTIONS = Counter("netanomaly_predictions_total", "Scored records", ["decision"], registry=REGISTRY)
SCORES = Histogram("netanomaly_anomaly_score", "Anomaly score of the served model (Isolation Forest about 0.3-0.8, LOF 1 and above)", registry=REGISTRY,
                   buckets=(0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0, 2.5, 3.0, 5.0, 10.0, 100.0))
BATCH_SIZE = Histogram("netanomaly_predict_batch_size", "Records per prediction request", registry=REGISTRY,
                       buckets=(1, 10, 50, 100, 200, 500, 1000))
INFERENCE_SECONDS = Histogram("netanomaly_model_inference_seconds", "Preprocessing and scoring time per request", registry=REGISTRY,
                              buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0))
DB_WRITE_ERRORS = Counter("netanomaly_db_write_errors_total", "Failed writes of predictions", registry=REGISTRY)
MODEL_INFO = Gauge("netanomaly_model_info", "Loaded model (value is always 1)", ["version"], registry=REGISTRY)
