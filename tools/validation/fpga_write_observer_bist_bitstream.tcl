# Generate a volatile-SRAM Observer BIST bitstream from an audited checkpoint.

set checkpoint [file normalize [lindex $argv 0]]
set output_bit [file normalize [lindex $argv 1]]
if {![file exists $checkpoint]} { error "Audited checkpoint not found: $checkpoint" }
set_param general.maxThreads 1
open_checkpoint $checkpoint
set unrouted [get_nets -quiet -filter {ROUTE_STATUS == UNROUTED}]
if {[llength $unrouted] != 0} { error "Checkpoint contains unrouted nets" }
# Compression reduced peak bitgen memory for the previously validated XC7Z045
# fabric build on this host, and also shortens the volatile JTAG download.
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]
write_bitstream -force $output_bit
if {![file exists $output_bit]} { error "Bitstream was not generated" }
puts "OUTPUT_BIT|$output_bit"
puts "OBSERVER_BIST_BITSTREAM_PASS|1"
close_design
exit 0
