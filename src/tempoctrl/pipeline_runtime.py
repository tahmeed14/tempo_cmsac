"""Formatting helpers for executable pipeline runtimes."""

from __future__ import annotations


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
