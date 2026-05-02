"""Structured logging via structlog — JSON in production, pretty in dev."""

import logging
import sys

import structlog

from app.core.config import settings


def configure_logging() -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.ENV == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO if settings.ENV == "production" else logging.DEBUG)
