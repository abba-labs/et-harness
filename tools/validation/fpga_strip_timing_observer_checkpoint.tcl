# Create a routed checkpoint without the timing database. The original audited
# checkpoint and reports remain the signoff evidence; this copy is for bounded
# bitstream generation only.

set input_checkpoint [file normalize [lindex $argv 0]]
set output_checkpoint [file normalize [lindex $argv 1]]
if {![file exists $input_checkpoint]} { error "Input checkpoint not found" }
set_param general.maxThreads 1
open_checkpoint $input_checkpoint
set unrouted [get_nets -quiet -filter {ROUTE_STATUS == UNROUTED}]
if {[llength $unrouted] != 0} { error "Input checkpoint contains unrouted nets" }
reset_timing
write_checkpoint -force $output_checkpoint
puts "STRIPPED_CHECKPOINT|$output_checkpoint"
puts "OBSERVER_BIST_STRIP_TIMING_PASS|1"
close_design
exit 0
