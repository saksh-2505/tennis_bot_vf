"""Platform entry point. Calls run_platform() from orchestrator.service."""
import logging

from config import settings
from database import check_connection, init_db
from observability import initialize_observability
from observability.logging import setup_structured_logging
from orchestrator.service import run_platform


def main() -> None:
    initialize_observability()
    setup_structured_logging(
        level=settings.LOG_LEVEL,
        service_name="app",
        module="main",
        component="platform",
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting Sports Trading Platform...")

    if check_connection():
        print("Database Connected")

    init_db()
    run_platform()


if __name__ == "__main__":
    main()
