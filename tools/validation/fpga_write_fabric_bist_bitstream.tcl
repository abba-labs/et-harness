# Generate the XC7Z045 Fabric BIST bitstream from an already routed and
# validated checkpoint in a fresh Vivado process to bound peak memory.

set checkpoint [file normalize [lindex $argv 0]]
set output_bit [file normalize [lindex $argv 1]]

if {![file exists $checkpoint]} {
    error "Routed checkpoint not found: $checkpoint"
}

set_param general.maxThreads 1
open_checkpoint $checkpoint

set unrouted_nets [get_nets -quiet -filter {ROUTE_STATUS == UNROUTED}]
puts "UNROUTED_NET_COUNT|[llength $unrouted_nets]"
if {[llength $unrouted_nets] != 0} {
    error "Checkpoint contains [llength $unrouted_nets] unrouted nets"
}

set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]
write_bitstream -force $output_bit

if {![file exists $output_bit]} {
    error "Bitstream was not generated: $output_bit"
}
puts "OUTPUT_BIT|$output_bit"
puts "FABRIC_BIST_BITSTREAM_PASS|1"
close_design
exit 0
