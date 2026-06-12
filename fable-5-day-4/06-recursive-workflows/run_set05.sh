#!/bin/bash
# Set 05 at n=10: recursive dynamic workflows, both variants, per-run dirs.
#   A (spec-driven bash chain): model at level N authors gen_L(N+1).sh from a shared
#     spec; success = gen-depth.log shows L2..L5 alive + L6 leaf line.
#   B (Node seed): L1 sonnet writes wf_L2.js, whose session writes wf_L3.js (2 haiku leaves).
# Usage: run_set05.sh [smoke]   (smoke = one run of each variant)
cd "$(dirname "$0")"
HERE=$(pwd)
OUT=../../output/fable5-n10
mkdir -p "$OUT/recwf-spec" "$OUT/recwf-node"
OUT=$(cd "$OUT" && pwd)
CSV="$OUT/set05.csv"
[ -f "$CSV" ] || echo "variant,run,seconds,pass,detail" > "$CSV"

run_spec() {
  local r=$1
  local dir="$OUT/recwf-spec/r$(printf '%02d' "$r")"
  mkdir -p "$dir"
  sed "s|@DIR@|$dir|g" "$HERE/recwf/gen_spec_template.md" > "$dir/gen_spec.md"
  local t0=$(date +%s)
  claude -p "Read $dir/gen_spec.md and execute the procedure with LEVEL=1" \
    --model sonnet --allowedTools "Bash,Write,Read" --permission-mode acceptEdits \
    < /dev/null > "$dir/seed_output.txt" 2>&1
  local t1=$(date +%s)
  local pass=FAIL
  if grep -q "L6: leaf, spec floor reached" "$dir/gen-depth.log" 2>/dev/null \
     && [ "$(grep -c "alive at" "$dir/gen-depth.log" 2>/dev/null)" -ge 5 ]; then
    pass=PASS
  fi
  local genned=$(ls "$dir"/gen_L*.sh 2>/dev/null | wc -l | tr -d ' ')
  echo "spec,$r,$((t1-t0)),$pass,genned=$genned" >> "$CSV"
  echo "spec r$r: $pass $((t1-t0))s genned=$genned"
}

run_node() {
  local r=$1
  local dir="$OUT/recwf-node/r$(printf '%02d' "$r")"
  mkdir -p "$dir"
  sed "s|@DIR@|$dir|g" "$HERE/recwf/wf_L1_template.js" > "$dir/wf_L1.js"
  local t0=$(date +%s)
  node "$dir/wf_L1.js" > "$dir/run_output.txt" 2>&1
  local t1=$(date +%s)
  local pass=FAIL
  if grep -q "L1 OK" "$dir/run_output.txt" && grep -q "L3 LEAF:" "$dir/run_output.txt"; then
    pass=PASS
  fi
  echo "node,$r,$((t1-t0)),$pass," >> "$CSV"
  echo "node r$r: $pass $((t1-t0))s"
}

case "$1" in
  smoke)     run_spec 0; run_node 0; exit 0 ;;
  nodesmoke) run_node 0; exit 0 ;;
  spec)
    for r in 1 2 3 4 5 6 7 8 9 10; do
      run_spec "$r" &
      while [ "$(jobs -r | wc -l)" -ge 3 ]; do wait -n; done
    done
    wait; echo "SET05 SPEC PHASE DONE"; exit 0 ;;
  node)
    for r in 1 2 3 4 5 6 7 8 9 10; do
      run_node "$r" &
      while [ "$(jobs -r | wc -l)" -ge 3 ]; do wait -n; done
    done
    wait; echo "SET05 NODE PHASE DONE"; exit 0 ;;
esac
echo "usage: run_set05.sh smoke|nodesmoke|spec|node"
