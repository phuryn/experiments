#!/bin/bash
# Harder effort sweep: verifiable math question (correct answer: 3 — the idempotents
# mod 1000 are 0, 1, 376, 625; positive n<1000 excluding trivial 1? No: 1, 376, 625 => 3)
cd /path/to/repo
QH="How many positive integers n < 1000 satisfy: n squared ends in exactly the same last three digits as n (treat n as zero-padded to 3 digits)? Work it out carefully, then answer with the number and the list of such n."
for eff in low medium high xhigh max; do
  start=$(date +%s.%N)
  out=$(claude -p "$QH" --model fable --effort "$eff" --disallowedTools "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch" 2>&1)
  rc=$?
  end=$(date +%s.%N)
  dur=$(echo "$end - $start" | bc)
  echo "--- FABLE-HARD effort=$eff rc=$rc time=${dur}s chars=${#out}"
  echo "$out" | tail -c 350
  echo; echo
done
echo "########## HARD SWEEP DONE ##########"
