#!/bin/bash

# cd "$(dirname "$0")"
# source .venv/bin/activate

python run_cm.py configs/cm_1.json &
python run_cm.py configs/cm_2.json &
python run_ca.py configs/ca_101.json &
# python run_ca.py configs/ca_102.json &