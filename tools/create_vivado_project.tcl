# Recreate the Vivado project from the command line.
#
# Usage:
#   vivado -mode batch -source tools/create_vivado_project.tcl -tclargs <part>
# Example:
#   vivado -mode batch -source tools/create_vivado_project.tcl -tclargs xc7a35tcpg236-1
#
# The part is a required argument because the original repository did not
# record the FPGA used for the Tech Vision 2026 demonstration.

if {$argc < 1} {
    puts "ERROR: pass the target part, e.g. -tclargs xc7a35tcpg236-1"
    exit 1
}
set part [lindex $argv 0]

set root [file normalize [file join [file dirname [info script]] ..]]
cd $root

create_project i2c_game_controller "$root/vivado" -part $part -force

add_files -norecurse [list \
    "$root/rtl/soc_top.v" \
    "$root/rtl/i2c_master_apb.v" \
    "$root/rtl/i2c_game_controller_slave.v" ]

add_files -fileset sim_1 -norecurse "$root/testbench/tb_soc_top.v"
add_files -fileset constrs_1 -norecurse "$root/constraints/soc_top.xdc"

set_property top soc_top [current_fileset]
set_property top tb_soc_top [get_filesets sim_1]
set_property top_lib xil_defaultlib [get_filesets sim_1]
set_property -name {xsim.simulate.runtime} -value {10us} -objects [get_filesets sim_1]

update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

puts "Vivado project created at $root/vivado"
puts "Run: launch_simulation -mode behavioral"
