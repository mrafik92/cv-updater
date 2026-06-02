"""Structured logging configuration for CV Tailor."""

from __future__ import annotations

import logging

import structlog


def _renderer_for_level(log_level: str) -> structlog.types.Processor:
    if log_level.upper() == "DEBUG":
        return structlog.dev.ConsoleRenderer()
    return structlog.processors.JSONRenderer()


def configure_logging(log_level: str = "INFO") -> None:
    level_name = log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(level=level, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            _renderer_for_level(level_name),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
