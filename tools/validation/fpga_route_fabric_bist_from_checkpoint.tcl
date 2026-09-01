# Resume XC7Z045 Fabric BIST routing from a placed checkpoint in a fresh
# Vivado process. This keeps each implementation stage below the workspace's
# per-process memory guard without weakening the guard policy.

set checkpoint [file normalize [lindex $argv 0]]
set output_dir [file normalize [lindex $argv 1]]

if {![file exists $checkpoint]} {
    error "Placed checkpoint not found: $checkpoint"
}
file mkdir $output_dir

open_checkpoint $checkpoint
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]

route_design -directive Quick

set unrouted_nets [get_nets -quiet -filter {ROUTE_STATUS == UNROUTED}]
puts "UNROUTED_NET_COUNT|[llength $unrouted_nets]"
if {[llength $unrouted_nets] != 0} {
    error "Routing left [llength $unrouted_nets] unrouted nets"
}

set drc_file [file join $output_dir "drc.rpt"]
set timing_file [file join $output_dir "timing_summary.rpt"]
set utilization_file [file join $output_dir "utilization_hierarchical.rpt"]
set methodology_file [file join $output_dir "methodology.rpt"]

report_drc -file $drc_file
report_timing_summary -file $timing_file
report_utilization -hierarchical -file $utilization_file
report_methodology -file $methodology_file

set fatal_drc [get_drc_violations -quiet -filter {SEVERITY == "Error" || SEVERITY == "Critical Warning"}]
puts "FATAL_DRC_COUNT|[llength $fatal_drc]"
if {[llength $fatal_drc] != 0} {
    foreach violation $fatal_drc {
        puts "FATAL_DRC|[get_property ID $violation]|[get_property SEVERITY $violation]"
    }
    error "Fatal DRC violations remain"
}

set worst_path [get_timing_paths -delay_type max -max_paths 1 -nworst 1]
if {[llength $worst_path] == 0} {
    error "No setup timing path was available"
}
set worst_slack [get_property SLACK $worst_path]
puts "WORST_SLACK_NS|$worst_slack"
if {$worst_slack < 0.0} {
    error "Timing failed with slack $worst_slack ns"
}

set routed_checkpoint [file join $output_dir "xc7z045_fabric_bist_routed.dcp"]
set output_bit [file join $output_dir "xc7z045_fabric_bist.bit"]
write_checkpoint -force $routed_checkpoint
write_bitstream -force $output_bit

puts "ROUTED_CHECKPOINT|$routed_checkpoint"
puts "OUTPUT_BIT|$output_bit"
puts "FABRIC_BIST_ROUTE_BUILD_PASS|1"
close_design
exit 0
