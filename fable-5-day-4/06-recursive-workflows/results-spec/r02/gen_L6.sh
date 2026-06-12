#!/usr/bin/env bash
echo "L6: orchestrator starting" >> <WORKDIR>/Temp/output/fable5-n10/recwf-spec/r02/gen-depth.log
claude -p "Read <WORKDIR>/Temp/output/fable5-n10/recwf-spec/r02/gen_spec.md and execute the procedure with LEVEL=6" --model sonnet --allowedTools "Bash,Write,Read" --permission-mode acceptEdits < /dev/null
