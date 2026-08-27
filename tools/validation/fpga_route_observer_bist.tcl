# Route the placed XC7Z045 Observer BIST in a fresh bounded Vivado process.

set checkpoint [file normalize [lindex $argv 0]]
set output_dir [file normalize [lindex $argv 1]]
set xdc_file [file normalize [lindex $argv 2]]
if {![file exists $checkpoint]} { error "Placed checkpoint not found: $checkpoint" }
if {![file exists $xdc_file]} { error "XDC not found: $xdc_file" }
file mkdir $output_dir
set_param general.maxThreads 1
open_checkpoint $checkpoint
reset_timing
read_xdc -unmanaged $xdc_file
update_timing
route_design

set unrouted [get_nets -quiet -filter {ROUTE_STATUS == UNROUTED}]
puts "UNROUTED_NET_COUNT|[llength $unrouted]"
if {[llength $unrouted] != 0} { error "Routing left unrouted nets" }

report_drc -file [file join $output_dir "drc.rpt"]
report_timing_summary -check_timing_verbose -file [file join $output_dir "timing_summary.rpt"]
report_methodology -file [file join $output_dir "methodology.rpt"]
report_utilization -hierarchical -file [file join $output_dir "utilization_hierarchical.rpt"]

set fatal_drc [get_drc_violations -quiet -filter {SEVERITY == "Error" || SEVERITY == "Critical Warning"}]
puts "FATAL_DRC_COUNT|[llength $fatal_drc]"
if {[llength $fatal_drc] != 0} { error "Fatal DRC violations remain" }

set setup_path [get_timing_paths -delay_type max -max_paths 1 -nworst 1]
if {[llength $setup_path] == 0} { error "No setup timing path was available" }
set setup_slack [get_property SLACK $setup_path]
puts "WORST_SETUP_SLACK_NS|$setup_slack"
if {$setup_slack < 0.0} { error "Setup timing failed" }

set routed_checkpoint [file join $output_dir "xc7z045_observer_bist_routed.dcp"]
write_checkpoint -force $routed_checkpoint
puts "ROUTED_CHECKPOINT|$routed_checkpoint"
puts "OBSERVER_BIST_ROUTE_PASS|1"
close_design
exit 0
