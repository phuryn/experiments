#!/bin/bash
echo "L3: orchestrator starting" >> "<WORKDIR>/Temp/output/fable5-n10/recwf10/r08/gen-depth.log"
claude -p "Read <WORKDIR>/Temp/output/fable5-n10/recwf10/r08/gen_spec.md and execute the procedure with LEVEL=3" --model haiku --allowedTools "Bash,Write,Read" --permission-mode acceptEdits < /dev/null
