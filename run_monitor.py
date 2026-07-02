"""Incident monitor entry point (Docker container)."""
import logging
import signal
import sys

from observability import initialize_observability
from observability.logging import setup_structured_logging


def main() -> None:
    initialize_observability()
    setup_structured_logging(
        service_name="monitor",
        module="run_monitor",
        component="incident_manager",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting Incident Monitor...")

    from incidents import monitor_platform

    def _handle_shutdown(signum, frame):
        logger.info("Shutdown signal received — stopping monitor")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    monitor_platform()


if __name__ == "__main__":
    main()
