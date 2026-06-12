#!/bin/bash
echo "L8: orchestrator starting" >> <WORKDIR>/Temp/output/fable5-n10/recwf10/r09/gen-depth.log
claude -p "Read <WORKDIR>/Temp/output/fable5-n10/recwf10/r09/gen_spec.md and execute the procedure with LEVEL=8" --model haiku --allowedTools "Bash,Write,Read" --permission-mode acceptEdits < /dev/null
