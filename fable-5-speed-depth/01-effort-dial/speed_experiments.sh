#!/bin/bash
# Experiment A: Fable effort levels (fixed no-tool question, timing = thinking+generation)
# Experiment B: 5 Opus vs 5 Fable on identical repo questions (1-2 file reads each)
cd /path/to/repo

QA="Explain in exactly 3 bullet points why nested subagents cost more than a flat fan-out of the same leaf tasks."

echo "########## EXPERIMENT A: Fable effort sweep ##########"
for eff in low medium high xhigh max; do
  start=$(date +%s.%N)
  out=$(claude -p "$QA" --model fable --effort "$eff" --disallowedTools "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch" 2>&1)
  rc=$?
  end=$(date +%s.%N)
  dur=$(echo "$end - $start" | bc)
  echo "--- FABLE effort=$eff rc=$rc time=${dur}s chars=${#out}"
  echo "$out" | head -c 400
  echo; echo
done

echo "########## EXPERIMENT B: Opus vs Fable, 5 repo questions ##########"
# NOTE: internal file paths/names genericized for publishing; prompt shape unchanged.
Q1="What tool does my project guide (CLAUDE.md) say to use for exporting infographics, and why not headless playwright? One sentence."
Q2="Per my paywall-strategy notes, where should the paywall cut land? One sentence."
Q3="What are the three buckets in Section 5.1 of this guide's draft? Three words."
Q4="What does my tools guide say is the cheapest data-fetching tool? One sentence."
Q5="How many lenses does my lenses index list? One number."

i=0
for q in "$Q1" "$Q2" "$Q3" "$Q4" "$Q5"; do
  i=$((i+1))
  for model in opus fable; do
    start=$(date +%s.%N)
    out=$(claude -p "$q" --model "$model" --disallowedTools "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch" 2>&1)
    rc=$?
    end=$(date +%s.%N)
    dur=$(echo "$end - $start" | bc)
    echo "--- Q$i model=$model rc=$rc time=${dur}s chars=${#out}"
    echo "$out" | head -c 250
    echo; echo
  done
done
echo "########## DONE ##########"
