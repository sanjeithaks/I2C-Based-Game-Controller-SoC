#!/bin/sh
# Simulate the I2C Game Controller SoC with Icarus Verilog (Linux/macOS).
set -e
cd "$(dirname "$0")/.."
mkdir -p sim
iverilog -g2012 -Wall -o sim/tb_soc_top.out \
    rtl/soc_top.v rtl/i2c_master_apb.v rtl/i2c_game_controller_slave.v \
    testbench/tb_soc_top.v
cd sim
vvp tb_soc_top.out | tee sim_log.txt
