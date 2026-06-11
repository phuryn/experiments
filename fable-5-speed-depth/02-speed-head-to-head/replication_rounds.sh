#!/bin/bash
# Replication: rounds 2-5 for (A) easy effort sweep, (B) realistic effort sweep,
# (C) Opus vs Fable 5-question speed test. Machine-parseable lines: RES,round,exp,key,q,rc,time,chars
cd /path/to/repo

QA="Explain in exactly 3 bullet points why nested subagents cost more than a flat fan-out of the same leaf tasks."
# NOTE: internal file paths/names genericized for publishing; prompt shape unchanged.
QM="Do my two craft style-guide files disagree about em dashes? Quote the load-bearing line from each, then reconcile any tension in under 120 words."
Q1="What tool does my project guide (CLAUDE.md) say to use for exporting infographics, and why not headless playwright? One sentence."
Q2="Per my paywall-strategy notes, where should the paywall cut land? One sentence."
Q3="What are the three buckets in Section 5.1 of this guide's draft? Three words."
Q4="What does my tools guide say is the cheapest data-fetching tool? One sentence."
Q5="How many lenses does my lenses index list? One number."
DENY="Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"

run() { # round exp key q prompt model effort
  local round=$1 exp=$2 key=$3 qn=$4 prompt=$5 model=$6 eff=$7
  local start end dur out rc
  start=$(date +%s.%N)
  if [ -n "$eff" ]; then
    out=$(claude -p "$prompt" --model "$model" --effort "$eff" --disallowedTools "$DENY" 2>&1)
  else
    out=$(claude -p "$prompt" --model "$model" --disallowedTools "$DENY" 2>&1)
  fi
  rc=$?
  end=$(date +%s.%N)
  dur=$(echo "$end - $start" | bc)
  echo "RES,$round,$exp,$key,$qn,$rc,$dur,${#out}"
}

for round in 2 3 4 5; do
  echo "===== ROUND $round ====="
  for eff in low medium high xhigh max; do
    run "$round" easy "$eff" QA "$QA" fable "$eff"
  done
  for eff in low medium high xhigh max; do
    run "$round" moderate "$eff" QM "$QM" fable "$eff"
  done
  i=0
  for q in "$Q1" "$Q2" "$Q3" "$Q4" "$Q5"; do
    i=$((i+1))
    run "$round" speed opus "Q$i" "$q" opus ""
    run "$round" speed fable "Q$i" "$q" fable ""
  done
done
echo "########## REPLICATION DONE ##########"
