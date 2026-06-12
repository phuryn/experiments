#!/bin/bash
# Set 04 at n=10: ten 6-level depth chains, 3 at a time, each in its own dir.
# Usage: run_set04.sh [smoke]   (smoke = one 3-level chain only)
cd "$(dirname "$0")"
OUT=../../output/fable5-n10/depth
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)

run_chain() {
  local c=$1 max=$2
  local dir="$OUT/c$(printf '%02d' "$c")"
  mkdir -p "$dir"
  local t0=$(date +%s)
  bash depth/level.sh 1 "$max" "$dir" > "$dir/root_output.txt" 2>&1
  local t1=$(date +%s)
  echo "CHAIN,$c,$max,$((t1-t0))s,$(head -c 200 "$dir/root_output.txt" | tr '\n' ' ')"
}

if [ "$1" = "smoke" ]; then
  run_chain 0 3
  exit 0
fi

for c in 1 2 3 4 5 6 7 8 9 10; do
  run_chain "$c" 6 &
  while [ "$(jobs -r | wc -l)" -ge 3 ]; do wait -n; done
done
wait
echo "SET04 DONE"
