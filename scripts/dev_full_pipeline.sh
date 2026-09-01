#!/usr/bin/env bash
set -euo pipefail

uv run python pipelines/pipeline_players.py
uv run python pipelines/pipeline_events.py
uv run python pipelines/pipeline_tracking.py
uv run python pipelines/pipeline_integrate.py
uv run python pipelines/pipeline_possessions.py
