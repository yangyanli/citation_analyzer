#!/bin/bash
set -e

# ==============================================================================
# run_examples.sh
# 
# This script runs a series of example tasks using predefined author/group IDs.
# It is useful for testing the pipeline on known entities or bootstrapping the 
# database with a few representative datasets.
# ==============================================================================

# Ensure we're running from the project root
if [ ! -d "backend" ]; then
  echo "Error: Please run this script from the root of the project (e.g., bash scripts/run_examples.sh)."
  exit 1
fi

export PYTHONPATH=.

# Optional args
PHASE_ARGS=""
RUN_ONLY_PHASE=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --run_only_phase) RUN_ONLY_PHASE="$2"; PHASE_ARGS="--run_only_phase $2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

if [ -z "$RUN_ONLY_PHASE" ]; then
    echo "Wiping old database..."
    rm -f data/citation_analyzer.db

    echo "Initializing Database..."
    venv/bin/python -c "from backend.database.sqlite_db import init_db; init_db()"

    echo "Seeding Database..."
    venv/bin/python backend/scripts/seed_db.py
else
    echo "Running isolated Phase $RUN_ONLY_PHASE. Skipping DB wipe and initialization."
fi

echo "Running task 1 (super admin, public group)"
venv/bin/python backend/main.py --user_id "9RxI7UAAAAAJ" --group_id 1 --non-interactive $PHASE_ARGS

echo "Running task 2 (wenzheng_chen, PKU VCL group)"
venv/bin/python backend/main.py --user_id "KzhR_TsAAAAJ" --group_id 2 --non-interactive $PHASE_ARGS

echo "Running task 3 (jinming_cao, Grab-NUS)"
venv/bin/python backend/main.py --user_id "GSte8PMAAAAJ" --group_id 3 --non-interactive $PHASE_ARGS

echo "All tasks completed."
