"""uptime-probe: a small HTTP availability monitor exposing Prometheus metrics."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, HttpUrl

from app.checker import Checker
from app.config import settings

logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")

checker = Checker(timeout_seconds=settings.timeout_seconds)
_state = {"ready": False}


@asynccontextmanager
async def lifespan(app: FastAPI):
    for url in settings.initial_target_list():
        checker.add(url)
    task = asyncio.create_task(checker.run_forever(settings.interval_seconds))
    _state["ready"] = True
    yield
    _state["ready"] = False
    task.cancel()


app = FastAPI(title="uptime-probe", version="0.1.0", lifespan=lifespan)


class TargetIn(BaseModel):
    url: HttpUrl


@app.get("/healthz", tags=["ops"])
def healthz() -> dict:
    """Liveness probe: the process is running."""
    return {"status": "ok"}


@app.get("/readyz", tags=["ops"])
def readyz() -> dict:
    """Readiness probe: the background checker has started."""
    if not _state["ready"]:
        raise HTTPException(status_code=503, detail="starting")
    return {"status": "ready"}


@app.get("/metrics", tags=["ops"])
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/targets", tags=["targets"])
def list_targets() -> list[dict]:
    return [vars(s) for s in checker.targets.values()]


@app.post("/targets", status_code=201, tags=["targets"])
async def add_target(body: TargetIn) -> dict:
    status = checker.add(str(body.url))
    return vars(status)


@app.delete("/targets", status_code=204, tags=["targets"])
def delete_target(url: str) -> Response:
    if not checker.remove(url):
        raise HTTPException(status_code=404, detail="target not found")
    return Response(status_code=204)


@app.post("/targets/check", tags=["targets"])
async def check_now() -> list[dict]:
    """Run one check cycle immediately (useful for smoke tests)."""
    return [vars(s) for s in await checker.check_all()]
