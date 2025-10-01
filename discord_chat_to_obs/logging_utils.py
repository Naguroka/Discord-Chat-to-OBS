from __future__ import annotations

import logging
import os


def configure_logging() -> None:
    """Initialize root logging to mirror the configured level."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
