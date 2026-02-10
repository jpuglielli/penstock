"""Demo: structlog integration.

Run this to see flow_id automatically injected into structlog output.
Note: requires `structlog` to be installed (pip install structlog).
"""

from __future__ import annotations

from penstock import current_flow_id, entrypoint, flow, step
from penstock.contrib.structlog import flow_processor

try:
    import structlog
except ImportError:
    print("This demo requires structlog: pip install structlog")
    raise SystemExit(1) from None

structlog.configure(
    processors=[
        flow_processor,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()


@flow("structlog_demo")
class Demo:
    @entrypoint
    def start(self) -> None:
        log.info("flow started", cid=current_flow_id())
        self.process()

    @step(after="start")
    def process(self) -> None:
        log.info("processing data")
        log.warning("something iffy", detail="check this")


if __name__ == "__main__":
    # Outside a flow — no flow_id injected.
    log.info("before flow")

    # Inside a flow — flow_id is injected automatically.
    Demo().start()

    # Outside again.
    log.info("after flow")
