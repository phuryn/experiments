#!/bin/bash
echo "L7: orchestrator starting" >> <WORKDIR>/Temp/output/fable5-n10/recwf10/r01/gen-depth.log
claude -p "Read <WORKDIR>/Temp/output/fable5-n10/recwf10/r01/gen_spec.md and execute the procedure with LEVEL=7" --model haiku --allowedTools "Bash,Write,Read" --permission-mode acceptEdits < /dev/null
