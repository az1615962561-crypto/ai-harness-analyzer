"""Structured logging configuration for AI Harness Analyzer."""
from __future__ import annotations

import logging
import sys

ROOT_LOGGER_NAME = "harness_analyzer"


def configure_logging(verbose: bool = False) -> logging.Logger:
    """Configure root package logger; keep default output quiet unless verbose=True."""
    logger = logging.getLogger(ROOT_LOGGER_NAME)
    level = logging.DEBUG if verbose else logging.WARNING
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
        )
        logger.addHandler(handler)

    for handler in logger.handlers:
        handler.setLevel(level)

    for noisy in ("httpx", "httpcore", "urllib3", "litellm"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under harness_analyzer."""
    if name.startswith(ROOT_LOGGER_NAME):
        return logging.getLogger(name)
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")
