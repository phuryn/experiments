#!/bin/bash
# Set 06 at n=10: nesting cost, 10 paired runs (flat + nested), pairs strictly
# serial, arm order alternating to cancel order effects. Wall + cost from CLI JSON.
# Usage: run_set06.sh [smoke]   (smoke = one flat run only)
cd "$(dirname "$0")"
OUT=../../output/fable5-n10/nestcost
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
CSV="$OUT/set06.csv"
[ -f "$CSV" ] || echo "pair,arm,order,seconds_wall,json" > "$CSV"

run_arm() { # pair arm order
  local pair=$1 arm=$2 order=$3
  local dir="$OUT/p$(printf '%02d' "$pair")-$arm"
  local t0=$(date +%s)
  node "nestcost/$arm.js" "$dir" > "$dir.stdout.txt" 2> "$dir.stderr.txt"
  local rc=$?
  local t1=$(date +%s)
  local line
  line=$(tail -1 "$dir.stdout.txt")
  echo "$pair,$arm,$order,$((t1-t0)),\"$line\"" >> "$CSV"
  echo "p$pair $arm ($order): rc=$rc $((t1-t0))s $line"
}

if [ "$1" = "smoke" ]; then
  run_arm 0 flat smoke
  exit 0
fi

for pair in 1 2 3 4 5 6 7 8 9 10; do
  if [ $((pair % 2)) -eq 1 ]; then
    run_arm "$pair" flat first
    run_arm "$pair" nested second
  else
    run_arm "$pair" nested first
    run_arm "$pair" flat second
  fi
done
echo "SET06 DONE"
