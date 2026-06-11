# Fable 5 experiment receipts (1/3): CLI depth chain, no cap outside the Task tool

Each level is a `claude -p` call (haiku) that spawns the next level via its Bash tool.
The platform's depth=5 subagent cap applies to the Task tool only; this chain hit no
resistance at any level. The floor at L6 is set by the script, not the platform.
Companion to: Claude Fable 5 for PMs: The Ultimate Guide, Section 7.2.

## level.sh (one script, recursion via argument)

```bash
#!/bin/bash
# CLI nesting depth test: each level is a claude -p (haiku) that spawns the next via Bash.
N=$1
MAX=$2
DIR=/path/to/repo/Temp/scripts/fable5-depth
date +"%s L$N start" >> $DIR/timeline.log
if [ "$N" -ge "$MAX" ]; then
  echo "L$N: floor reached, no spawn" > $DIR/level_$N.txt
  echo "FLOOR $N"
  exit 0
fi
NEXT=$((N+1))
OUT=$(claude -p --model haiku --allowedTools Bash --permission-mode acceptEdits \
  "You are depth-test agent L$N. Do exactly two things: (1) run this bash command: bash $DIR/level.sh $NEXT $MAX  (2) after it finishes, output a single line: L$N OK, child said: <first line of the command output>. Nothing else." 2>>$DIR/err_$N.log)
echo "L$N spawned L$NEXT. claude output: $OUT" > $DIR/level_$N.txt
date +"%s L$N done" >> $DIR/timeline.log
echo "$OUT"
```

## depth_chain.sh (desktop variant of the same chain)

```bash
#!/bin/bash
LVL=$1
LOG=/path/to/repo/Temp/output/cli-depth.log
echo "L${LVL}: claude process alive at $(date +%H:%M:%S)" >> "$LOG"
if [ "$LVL" -lt 6 ]; then
  NEXT=$((LVL+1))
  IS_SANDBOX=1 claude -p "Use your Bash tool to run exactly this command: bash /path/to/repo/Temp/scripts/depth_chain.sh ${NEXT}  -- then reply with exactly: L${NEXT} dispatched" --model haiku --dangerously-skip-permissions < /dev/null 2>>"$LOG"
else
  echo "L${LVL}: leaf reached, stopping by design (script floor, not platform)" >> "$LOG"
fi
```

## timeline.log (unix epoch: start/done per level)

```
1781071067 L1 start
1781071071 L2 start
1781071075 L3 start
1781071079 L4 start
1781071083 L5 start
1781071091 L6 start
1781071094 L5 done
1781071097 L4 done
1781071100 L3 done
1781071104 L2 done
1781071111 L1 done
```

## Per-level outputs

```
L1 spawned L2. claude output: L1 OK, child said: L2 OK, child said: L3 OK, child said: L4 OK, child said: L5 OK, child said: FLOOR 6
L2 spawned L3. claude output: L2 OK, child said: L3 OK, child said: L4 OK, child said: L5 OK, child said: FLOOR 6
L3 spawned L4. claude output: L3 OK, child said: L4 OK, child said: L5 OK, child said: FLOOR 6
L4 spawned L5. claude output: L4 OK, child said: L5 OK, child said: FLOOR 6
L5 spawned L6. claude output: L5 OK, child said: FLOOR 6
L6: floor reached, no spawn
```
