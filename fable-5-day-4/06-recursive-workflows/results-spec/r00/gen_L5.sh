#!/usr/bin/env bash
echo "L5: orchestrator starting" >> <WORKDIR>/Temp/output/fable5-n10/recwf-spec/r00/gen-depth.log
claude -p "Read <WORKDIR>/Temp/output/fable5-n10/recwf-spec/r00/gen_spec.md and execute the procedure with LEVEL=5" --model sonnet --allowedTools "Bash,Write,Read" --permission-mode acceptEdits < /dev/null
