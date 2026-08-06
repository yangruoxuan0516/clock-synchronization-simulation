#!/bin/bash

cd "$(dirname "$0")" || exit 1

PYTHON="$PWD/.venv/bin/python3"

"$PYTHON" run_cm.py configs/cm_1.json &
"$PYTHON" run_cm.py configs/cm_2.json &
"$PYTHON" run_ca.py configs/ca_101.json &
"$PYTHON" run_ca.py configs/ca_102.json &

wait