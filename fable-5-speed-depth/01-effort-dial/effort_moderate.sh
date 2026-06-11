#!/bin/bash
# Moderate/judgment task sweep: repo reasoning with tool use (2 file reads + reconciliation)
cd /path/to/repo
# NOTE: internal file paths/names genericized below for publishing; the shape of each prompt is unchanged.
QM="Do my two craft style-guide files disagree about em dashes? Quote the load-bearing line from each, then reconcile any tension in under 120 words."
for eff in low medium high xhigh max; do
  start=$(date +%s.%N)
  out=$(claude -p "$QM" --model fable --effort "$eff" --disallowedTools "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch" 2>&1)
  rc=$?
  end=$(date +%s.%N)
  dur=$(echo "$end - $start" | bc)
  echo "--- FABLE-MOD effort=$eff rc=$rc time=${dur}s chars=${#out}"
  echo "$out" | head -c 500
  echo; echo
done
# Variance check: re-run the Q4 outlier from Experiment B once per model
QV="What does my tools guide say is the cheapest data-fetching tool? One sentence."
for model in opus fable; do
  start=$(date +%s.%N)
  out=$(claude -p "$QV" --model "$model" --disallowedTools "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch" 2>&1)
  end=$(date +%s.%N)
  dur=$(echo "$end - $start" | bc)
  echo "--- VARIANCE-Q4 model=$model time=${dur}s chars=${#out}"
done
echo "########## MODERATE SWEEP DONE ##########"
