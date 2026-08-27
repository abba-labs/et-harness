# Final timing/DRC/methodology audit for the routed Observer BIST.

set checkpoint [file normalize [lindex $argv 0]]
set xdc_file [file normalize [lindex $argv 1]]
set output_dir [file normalize [lindex $argv 2]]
if {![file exists $checkpoint]} { error "Routed checkpoint not found: $checkpoint" }
if {![file exists $xdc_file]} { error "XDC not found: $xdc_file" }
file mkdir $output_dir
set_param general.maxThreads 1
open_checkpoint $checkpoint
reset_timing
read_xdc -unmanaged $xdc_file
update_timing

report_timing_summary -check_timing_verbose -file [file join $output_dir "timing_summary_audited.rpt"]
report_methodology -file [file join $output_dir "methodology_audited.rpt"]
report_drc -file [file join $output_dir "drc_audited.rpt"]
report_io -file [file join $output_dir "observer_io_audited.rpt"]

set setup_path [get_timing_paths -delay_type max -max_paths 1 -nworst 1]
set hold_path [get_timing_paths -delay_type min -max_paths 1 -nworst 1]
if {[llength $setup_path] == 0 || [llength $hold_path] == 0} {
    error "Setup or hold timing path unavailable"
}
set setup_slack [get_property SLACK $setup_path]
set hold_slack [get_property SLACK $hold_path]
puts "WORST_SETUP_SLACK_NS|$setup_slack"
puts "WORST_HOLD_SLACK_NS|$hold_slack"
if {$setup_slack < 0.0 || $hold_slack < 0.0} { error "Audited timing failed" }

set fatal_drc [get_drc_violations -quiet -filter {SEVERITY == "Error" || SEVERITY == "Critical Warning"}]
puts "FATAL_DRC_COUNT|[llength $fatal_drc]"
if {[llength $fatal_drc] != 0} { error "Fatal DRC violations remain" }

set critical_methodology [get_methodology_violations -quiet -filter {SEVERITY == "Critical Warning"}]
puts "CRITICAL_METHODOLOGY_COUNT|[llength $critical_methodology]"
if {[llength $critical_methodology] != 0} {
    foreach violation $critical_methodology {
        puts "CRITICAL_METHODOLOGY|[get_property ID $violation]"
    }
    error "Critical methodology violations remain"
}

set audited_checkpoint [file join $output_dir "xc7z045_observer_bist_audited.dcp"]
write_checkpoint -force $audited_checkpoint
puts "AUDITED_CHECKPOINT|$audited_checkpoint"
puts "OBSERVER_BIST_AUDIT_PASS|1"
close_design
exit 0
