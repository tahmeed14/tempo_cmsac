#!/usr/bin/env bash
set -euo pipefail

script_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repository_root=$(cd -- "${script_directory}/.." && pwd)
cd "${repository_root}"

run_step() {
    local description=$1
    shift

    echo "Reproducing ${description}..."
    "$@"
}

run_step "summary-statistics table" \
    uv run python -m tempoctrl.reproduce_tables
run_step "fixed-effects tables" \
    uv run python -m tempoctrl.reproduce_fixed_effects_tables
run_step "random-effects tables" \
    uv run python -m tempoctrl.reproduce_random_effects_table
run_step "player-archetype overlap tables" \
    uv run python -m tempoctrl.reproduce_re_and_case_studies
run_step "player-archetype figures" \
    uv run python -m tempoctrl.reproduce_archetypes
run_step "remaining paper figures" \
    uv run python -m tempoctrl.reproduce_figures

echo "Paper figures and tables reproduced successfully."
