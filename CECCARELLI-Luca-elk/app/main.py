import logging
import sys
import time
import uuid
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from pythonjsonlogger import jsonlogger

# ---------------------------------------------------------------------------
# Structured JSON logger
# ---------------------------------------------------------------------------
_handler = logging.StreamHandler(sys.stdout)
_formatter = jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    rename_fields={"asctime": "@timestamp", "levelname": "level", "name": "logger"},
)
_handler.setFormatter(_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [_handler]

logger = logging.getLogger("app")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="tpmetrics-elk-app")


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    path = request.url.path
    method = request.method
    status_code = 500

    # Attach request_id so route handlers can read it
    request.state.request_id = request_id

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        logger.error(
            "Unhandled exception",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "error": str(exc),
            },
        )
        raise
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        level = logging.ERROR if status_code >= 500 else (
            logging.WARNING if status_code >= 400 else logging.INFO
        )
        logger.log(
            level,
            "HTTP request",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "status_family": f"{status_code // 100}xx",
                "duration_ms": duration_ms,
            },
        )

    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    logger.info("Health check", extra={"action": "health_check"})
    return {"status": "ok"}


@app.get("/ok")
def ok(request: Request) -> dict:
    logger.info(
        "Nominal request",
        extra={"action": "nominal", "request_id": getattr(request.state, "request_id", None)},
    )
    return {"message": "success"}


@app.get("/not-found")
def not_found(request: Request) -> None:
    logger.warning(
        "Resource not found",
        extra={
            "action": "not_found",
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    raise HTTPException(status_code=404, detail="resource not found")


@app.get("/error")
def error(request: Request) -> None:
    logger.error(
        "Forced server error",
        extra={
            "action": "forced_error",
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    raise HTTPException(status_code=500, detail="forced server error")


@app.post("/process")
def process(request: Request, items: int = 1, delay_ms: int = 50) -> dict:
    request_id = getattr(request.state, "request_id", None)
    if items < 1:
        logger.warning(
            "Invalid items parameter",
            extra={"action": "process", "request_id": request_id, "items": items},
        )
        raise HTTPException(status_code=400, detail="items must be >= 1")
    if delay_ms < 0:
        logger.warning(
            "Invalid delay_ms parameter",
            extra={"action": "process", "request_id": request_id, "delay_ms": delay_ms},
        )
        raise HTTPException(status_code=400, detail="delay_ms must be >= 0")

    logger.info(
        "Processing items",
        extra={"action": "process_start", "request_id": request_id, "items": items, "delay_ms": delay_ms},
    )
    if delay_ms > 0:
        time.sleep(delay_ms / 1000)
    logger.info(
        "Items processed",
        extra={"action": "process_done", "request_id": request_id, "items": items},
    )
    return {"processed_items": items, "delay_ms": delay_ms}


@app.post("/order")
def create_order(request: Request, product_id: str = "PROD-001", quantity: int = 1) -> dict:
    """Business route: creates a fake order — illustrates domain-level logs."""
    request_id = getattr(request.state, "request_id", None)

    if quantity < 1 or quantity > 100:
        logger.warning(
            "Order rejected: invalid quantity",
            extra={
                "action": "order_rejected",
                "request_id": request_id,
                "product_id": product_id,
                "quantity": quantity,
                "reason": "quantity_out_of_range",
            },
        )
        raise HTTPException(status_code=400, detail="quantity must be between 1 and 100")

    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    logger.info(
        "Order created",
        extra={
            "action": "order_created",
            "request_id": request_id,
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
        },
    )
    return {"order_id": order_id, "product_id": product_id, "quantity": quantity, "status": "created"}
