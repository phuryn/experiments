# Recursive workflow depth test — spec10 (set 08, per-run dir: @DIR@)

You are the agent at LEVEL N (N is given in your prompt as LEVEL=N). Follow exactly:

1. Append one line to @DIR@/gen-depth.log:
   "L<N>: alive at <HH:MM:SS>, my orchestrator was written by L<N-1>"
2. If N >= 10: append "L<N>: leaf, spec floor reached" to the same log, reply "done", and STOP. Do not write any script.
3. Otherwise, WRITE a new bash script at @DIR@/gen_L<N+1>.sh (you are authoring the next level's orchestrator) that does exactly:
   - appends "L<N+1>: orchestrator starting" to @DIR@/gen-depth.log
   - runs: claude -p "Read @DIR@/gen_spec.md and execute the procedure with LEVEL=<N+1>" --model haiku --allowedTools "Bash,Write,Read" --permission-mode acceptEdits < /dev/null
4. Execute it: bash @DIR@/gen_L<N+1>.sh
5. Reply "done".

Replace every <N>, <N-1>, <N+1> with actual numbers. Keep the log lines exact.
