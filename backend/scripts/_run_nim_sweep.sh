#!/usr/bin/env bash
# Phase-2 NIM blind-answer sweep driver.
# Runs all 18 MCQ cells SEQUENTIALLY at 2 workers (rate-limit friendly),
# in priority order. Each cell is independently resumable via its sidecar.
# Re-running this script resumes any incomplete cell from where it stalled.
set -u
cd "$(dirname "$0")/../.." || exit 1
PY=.venv/bin/python
H=backend/scripts/audit_blind_answer_nim.py

# Priority order: defect-catching tracks (mlf, exp) first, then the rest.
CELLS=(
  "ml-fundamentals hard"
  "experimentation hard"
  "experimentation medium"
  "ml-fundamentals medium"
  "pyspark hard"
  "pyspark medium"
  "pyspark easy"
  "data-engineering hard"
  "data-engineering medium"
  "data-engineering easy"
  "data-modeling hard"
  "data-modeling medium"
  "data-modeling easy"
  "statistics hard"
  "statistics medium"
  "statistics easy"
  "ml-fundamentals easy"
  "experimentation easy"
)

i=0
n=${#CELLS[@]}
for cell in "${CELLS[@]}"; do
  i=$((i+1))
  set -- $cell
  track=$1; diff=$2
  echo ""
  echo "############################################################"
  echo "## CELL $i/$n : $track $diff   ($(date '+%H:%M:%S'))"
  echo "############################################################"
  $PY "$H" --track "$track" --difficulty "$diff" --workers 2
  echo "## CELL $i/$n DONE : $track $diff   ($(date '+%H:%M:%S'))"
done
echo ""
echo "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
echo "@@@ ALL 18 CELLS COMPLETE   ($(date '+%H:%M:%S'))"
echo "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
