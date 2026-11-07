"""HTTP availability checker that exports results as Prometheus metrics."""

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx
from prometheus_client import Counter, Gauge, Histogram

log = logging.getLogger("uptime_probe.checker")

PROBE_UP = Gauge("probe_target_up", "1 if the last check succeeded, 0 otherwise", ["target"])
PROBE_LATENCY = Histogram(
    "probe_target_latency_seconds",
    "HTTP response time of the target",
    ["target"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
PROBE_CHECKS = Counter("probe_checks_total", "Checks executed", ["target", "result"])


@dataclass
class TargetStatus:
    url: str
    up: bool | None = None
    status_code: int | None = None
    latency_seconds: float | None = None
    last_checked: float | None = None
    error: str | None = None


@dataclass
class Checker:
    timeout_seconds: float = 5.0
    transport: httpx.AsyncBaseTransport | None = None
    targets: dict[str, TargetStatus] = field(default_factory=dict)

    def add(self, url: str) -> TargetStatus:
        return self.targets.setdefault(url, TargetStatus(url=url))

    def remove(self, url: str) -> bool:
        if self.targets.pop(url, None) is None:
            return False
        for metric in (PROBE_UP, PROBE_LATENCY):
            try:
                metric.remove(url)
            except KeyError:
                pass
        return True

    async def check(self, client: httpx.AsyncClient, status: TargetStatus) -> TargetStatus:
        start = time.perf_counter()
        try:
            resp = await client.get(status.url)
            status.status_code = resp.status_code
            status.up = resp.status_code < 400
            status.error = None
        except httpx.HTTPError as exc:
            status.status_code = None
            status.up = False
            status.error = type(exc).__name__
        status.latency_seconds = time.perf_counter() - start
        status.last_checked = time.time()

        PROBE_UP.labels(status.url).set(1 if status.up else 0)
        PROBE_LATENCY.labels(status.url).observe(status.latency_seconds)
        PROBE_CHECKS.labels(status.url, "up" if status.up else "down").inc()
        if not status.up:
            log.warning("target down: %s (%s)", status.url, status.error or status.status_code)
        return status

    async def check_all(self) -> list[TargetStatus]:
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds, follow_redirects=True, transport=self.transport
        ) as client:
            return await asyncio.gather(*(self.check(client, s) for s in list(self.targets.values())))

    async def run_forever(self, interval_seconds: float) -> None:
        while True:
            try:
                await self.check_all()
            except Exception:  # never let the loop die
                log.exception("check cycle failed")
            await asyncio.sleep(interval_seconds)
