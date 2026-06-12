#!/bin/bash
# CLI nesting depth test (set 04, n=10): each level is a claude -p (haiku) that
# spawns the next via its Bash tool. Per-chain DIR isolates concurrent chains.
# Usage: level.sh <N> <MAX> <DIR>
N=$1
MAX=$2
DIR=$3
date +"%s L$N start" >> "$DIR/timeline.log"
if [ "$N" -ge "$MAX" ]; then
  echo "L$N: floor reached, no spawn" > "$DIR/level_$N.txt"
  echo "FLOOR $N"
  exit 0
fi
NEXT=$((N+1))
SCRIPT="$(cd "$(dirname "$0")" && pwd)/level.sh"
OUT=$(claude -p --model haiku --allowedTools Bash --permission-mode acceptEdits \
  "You are depth-test agent L$N. Do exactly two things: (1) run this bash command: bash $SCRIPT $NEXT $MAX $DIR  (2) after it finishes, output a single line: L$N OK, child said: <first line of the command output>. Nothing else." 2>>"$DIR/err_$N.log")
echo "L$N spawned L$NEXT. claude output: $OUT" > "$DIR/level_$N.txt"
date +"%s L$N done" >> "$DIR/timeline.log"
echo "$OUT"
