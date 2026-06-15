import time
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

app = FastAPI(title="tpmetrics-app")

HTTP_REQUESTS_TOTAL = Counter(
    "app_http_requests_total",
    "Total HTTP requests served by the application",
    ["method", "path", "status_code", "status_family"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "app_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "status_family"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

PROCESSED_ITEMS_TOTAL = Counter(
    "app_processed_items_total",
    "Total number of business items processed",
)

IN_PROGRESS_JOBS = Gauge(
    "app_in_progress_jobs",
    "Number of currently running processing jobs",
)


def _family(status_code: int) -> str:
    return f"{status_code // 100}xx"


@app.middleware("http")
async def instrument_requests(request: Request, call_next: Callable) -> Response:
    start = time.perf_counter()
    path = request.url.path
    method = request.method
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        duration = time.perf_counter() - start
        status_family = _family(status_code)
        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            path=path,
            status_code=str(status_code),
            status_family=status_family,
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            path=path,
            status_family=status_family,
        ).observe(duration)

    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ok")
def ok() -> dict:
    return {"message": "success"}


@app.get("/not-found")
def not_found() -> None:
    raise HTTPException(status_code=404, detail="forced 404 for traffic testing")


@app.get("/error")
def error() -> None:
    raise HTTPException(status_code=500, detail="forced 500 for traffic testing")


@app.post("/process")
def process(items: int = 1, delay_ms: int = 50) -> dict:
    if items < 1:
        raise HTTPException(status_code=400, detail="items must be >= 1")
    if delay_ms < 0:
        raise HTTPException(status_code=400, detail="delay_ms must be >= 0")

    IN_PROGRESS_JOBS.inc()
    try:
        if delay_ms > 0:
            time.sleep(delay_ms / 1000)
        PROCESSED_ITEMS_TOTAL.inc(items)
    finally:
        IN_PROGRESS_JOBS.dec()

    return {"processed_items": items, "delay_ms": delay_ms}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
