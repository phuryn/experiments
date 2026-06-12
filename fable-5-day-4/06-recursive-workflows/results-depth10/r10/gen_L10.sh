#!/bin/bash
echo "L10: orchestrator starting" >> <WORKDIR>/Temp/output/fable5-n10/recwf10/r10/gen-depth.log
claude -p "Read <WORKDIR>/Temp/output/fable5-n10/recwf10/r10/gen_spec.md and execute the procedure with LEVEL=10" --model haiku --allowedTools "Bash,Write,Read" --permission-mode acceptEdits < /dev/null
