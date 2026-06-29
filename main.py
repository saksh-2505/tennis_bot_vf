"""Platform entry point. Calls run_platform() from orchestrator.service."""
import logging

from database import check_connection, init_db
from logger import setup_logging
from orchestrator.service import run_platform


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Sports Trading Platform...")

    if check_connection():
        print("Database Connected")

    init_db()
    run_platform()


if __name__ == "__main__":
    main()
