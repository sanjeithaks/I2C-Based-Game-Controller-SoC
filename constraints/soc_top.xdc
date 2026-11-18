# Timing constraint for `soc_top`
#
# The design is synchronous to `clk`; SCL is generated from `clk` by the
# I2C master and the game-controller slave is clocked by `clk` as well.
create_clock -period 10.000 -name clk [get_ports clk]

# SDA is an open-drain line. Implement it with an IOBUF (or an equivalent
# tri-state buffer) and fit an external pull-up resistor on the board.
#
# Board-specific pin assignments are intentionally not included: they depend
# on the target FPGA and package. Add them here for your board.
