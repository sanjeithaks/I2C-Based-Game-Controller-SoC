# Simulate the I2C Game Controller SoC with Icarus Verilog.
# Usage:  powershell -ExecutionPolicy Bypass -File tools\run_sim.ps1
#         powershell -ExecutionPolicy Bypass -File tools\run_sim.ps1 -Iverilog "C:\iverilog\bin\iverilog.exe" -Vvp "C:\iverilog\bin\vvp.exe"

param(
    [string]$Iverilog = "iverilog",
    [string]$Vvp      = "vvp"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

New-Item -ItemType Directory -Force -Path sim | Out-Null

& $Iverilog -g2012 -Wall -o sim/tb_soc_top.out `
    rtl/soc_top.v rtl/i2c_master_apb.v rtl/i2c_game_controller_slave.v `
    testbench/tb_soc_top.v

if ($LASTEXITCODE -ne 0) { throw "Compilation failed" }

Push-Location sim
$output = & $Vvp tb_soc_top.out 2>&1
$code = $LASTEXITCODE
$output | ForEach-Object { Write-Host $_ }
$output | Set-Content -Path sim_log.txt -Encoding utf8
Pop-Location

if ($code -ne 0) { throw "Simulation failed" }
Write-Host "Simulation finished. Log: sim/sim_log.txt  Waveform: sim/dump.vcd"
