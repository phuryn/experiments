# Recursive workflow depth test — spec10 (set 08, per-run dir: <WORKDIR>/Temp/output/fable5-n10/recwf10/r07)

You are the agent at LEVEL N (N is given in your prompt as LEVEL=N). Follow exactly:

1. Append one line to <WORKDIR>/Temp/output/fable5-n10/recwf10/r07/gen-depth.log:
   "L<N>: alive at <HH:MM:SS>, my orchestrator was written by L<N-1>"
2. If N >= 10: append "L<N>: leaf, spec floor reached" to the same log, reply "done", and STOP. Do not write any script.
3. Otherwise, WRITE a new bash script at <WORKDIR>/Temp/output/fable5-n10/recwf10/r07/gen_L<N+1>.sh (you are authoring the next level's orchestrator) that does exactly:
   - appends "L<N+1>: orchestrator starting" to <WORKDIR>/Temp/output/fable5-n10/recwf10/r07/gen-depth.log
   - runs: claude -p "Read <WORKDIR>/Temp/output/fable5-n10/recwf10/r07/gen_spec.md and execute the procedure with LEVEL=<N+1>" --model haiku --allowedTools "Bash,Write,Read" --permission-mode acceptEdits < /dev/null
4. Execute it: bash <WORKDIR>/Temp/output/fable5-n10/recwf10/r07/gen_L<N+1>.sh
5. Reply "done".

Replace every <N>, <N-1>, <N+1> with actual numbers. Keep the log lines exact.
