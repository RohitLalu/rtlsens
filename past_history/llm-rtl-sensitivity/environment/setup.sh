#!/usr/bin/env bash
# Install tools and pin the VerilogEval checkout. Tested on Ubuntu 24.04.
set -euo pipefail
VERILOG_EVAL_COMMIT=c498220d0a52248f8e3fdffe279075215bde2da6

sudo apt-get update
sudo apt-get install -y iverilog yosys          # Icarus 12.x and Yosys from the distribution
iverilog -V | head -1
yosys -V

python3 -m pip install -e ".[test]"

mkdir -p third_party
if [ ! -d third_party/verilog-eval ]; then
  git clone https://github.com/NVlabs/verilog-eval third_party/verilog-eval
fi
git -C third_party/verilog-eval checkout "$VERILOG_EVAL_COMMIT"
echo "VerilogEval pinned at $(git -C third_party/verilog-eval rev-parse HEAD)"
