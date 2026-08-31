"""Runtime logging helpers for executable data pipelines."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter


def format_pipeline_runtime(elapsed_seconds: float) -> str:
    """Format elapsed seconds as hours, minutes, and seconds."""
    hours, remaining_seconds = divmod(elapsed_seconds, 3_600)
    minutes, seconds = divmod(remaining_seconds, 60)
    hour_count = int(hours)
    minute_count = int(minutes)
    hour_unit = "hour" if hour_count == 1 else "hours"
    minute_unit = "minute" if minute_count == 1 else "minutes"
    return (
        f"{hour_count} {hour_unit}, "
        f"{minute_count} {minute_unit}, "
        f"{seconds:.3f} seconds"
    )


@contextmanager
def log_pipeline_runtime(
    logger: logging.Logger,
    pipeline_name: str,
) -> Iterator[None]:
    """Log the total runtime when a pipeline scope exits."""
    started_at = perf_counter()
    try:
        yield
    finally:
        elapsed_seconds = perf_counter() - started_at
        logger.info(
            "%s pipeline runtime: %s",
            pipeline_name,
            format_pipeline_runtime(elapsed_seconds),
        )
