# Optimize and place a synthesized Observer BIST checkpoint in a fresh process.

set checkpoint [file normalize [lindex $argv 0]]
set output_dir [file normalize [lindex $argv 1]]
if {![file exists $checkpoint]} { error "Synthesis checkpoint not found: $checkpoint" }
file mkdir $output_dir
set_param general.maxThreads 1
open_checkpoint $checkpoint
opt_design
place_design -directive Quick
report_io -file [file join $output_dir "observer_io_placed.rpt"]
report_utilization -hierarchical -file [file join $output_dir "utilization_placed.rpt"]
report_timing_summary -file [file join $output_dir "timing_placed.rpt"]
set placed_checkpoint [file join $output_dir "xc7z045_observer_bist_placed.dcp"]
write_checkpoint -force $placed_checkpoint
puts "PLACED_CHECKPOINT|$placed_checkpoint"
puts "OBSERVER_BIST_PLACE_PASS|1"
close_design
exit 0
