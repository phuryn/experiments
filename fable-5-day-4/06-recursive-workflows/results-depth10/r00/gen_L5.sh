#!/bin/bash
printf 'L5: orchestrator starting\n' >> "<WORKDIR>/Temp/output/fable5-n10/recwf10/r00/gen-depth.log"
claude -p "Read <WORKDIR>/Temp/output/fable5-n10/recwf10/r00/gen_spec.md and execute the procedure with LEVEL=5" --model haiku --allowedTools "Bash,Write,Read" --permission-mode acceptEdits < /dev/null
