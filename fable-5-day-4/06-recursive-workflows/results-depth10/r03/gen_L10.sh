#!/bin/bash

# Append orchestrator starting message
echo "L10: orchestrator starting" >> "<WORKDIR>/Temp/output/fable5-n10/recwf10/r03/gen-depth.log"

# Run the next level agent
claude -p "Read <WORKDIR>/Temp/output/fable5-n10/recwf10/r03/gen_spec.md and execute the procedure with LEVEL=10" --model haiku --allowedTools "Bash,Write,Read" --permission-mode acceptEdits < /dev/null
