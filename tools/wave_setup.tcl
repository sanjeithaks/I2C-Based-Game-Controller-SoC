set sigs [list \
    tb_soc_top.clk \
    tb_soc_top.reset \
    tb_soc_top.apb_start \
    tb_soc_top.dut.master.apb_done \
    tb_soc_top.scl \
    tb_soc_top.sda \
    tb_soc_top.slave_addr \
    tb_soc_top.controller_buttons \
    tb_soc_top.button_status \
    tb_soc_top.dut.master.state \
    tb_soc_top.dut.master.bit_cnt \
    tb_soc_top.dut.master.shift_reg \
    tb_soc_top.dut.slave.state \
    tb_soc_top.dut.slave.addr_match \
    tb_soc_top.dut.slave.sda_drive ]

gtkwave::addSignalsFromList $sigs
gtkwave::/Time/Zoom/Zoom_Full
gtkwave::setWindowTitle "GTKWave - I2C Game Controller SoC - dump.vcd"
