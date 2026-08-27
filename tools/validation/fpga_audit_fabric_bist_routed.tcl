# Re-apply the source timing constraints to an already routed checkpoint,
# verify setup/hold timing and methodology, then save an audited checkpoint.

set input_checkpoint [file normalize [lindex $argv 0]]
set xdc_file [file normalize [lindex $argv 1]]
set output_dir [file normalize [lindex $argv 2]]

if {![file exists $input_checkpoint]} {
    error "Routed checkpoint not found: $input_checkpoint"
}
if {![file exists $xdc_file]} {
    error "Constraint file not found: $xdc_file"
}
file mkdir $output_dir

set_param general.maxThreads 1
open_checkpoint $input_checkpoint
reset_timing
read_xdc -unmanaged $xdc_file
update_timing

set timing_file [file join $output_dir "timing_summary_audited.rpt"]
set methodology_file [file join $output_dir "methodology_audited.rpt"]
set drc_file [file join $output_dir "drc_audited.rpt"]

report_timing_summary -check_timing_verbose -file $timing_file
report_methodology -file $methodology_file
report_drc -file $drc_file

set worst_setup_path [get_timing_paths -delay_type max -max_paths 1 -nworst 1]
set worst_hold_path [get_timing_paths -delay_type min -max_paths 1 -nworst 1]
if {[llength $worst_setup_path] == 0 || [llength $worst_hold_path] == 0} {
    error "Setup or hold timing path is unavailable"
}
set worst_setup_slack [get_property SLACK $worst_setup_path]
set worst_hold_slack [get_property SLACK $worst_hold_path]
puts "WORST_SETUP_SLACK_NS|$worst_setup_slack"
puts "WORST_HOLD_SLACK_NS|$worst_hold_slack"
if {$worst_setup_slack < 0.0 || $worst_hold_slack < 0.0} {
    error "Audited timing failed"
}

set fatal_drc [get_drc_violations -quiet -filter {SEVERITY == "Error" || SEVERITY == "Critical Warning"}]
puts "FATAL_DRC_COUNT|[llength $fatal_drc]"
if {[llength $fatal_drc] != 0} {
    error "Fatal DRC violations remain"
}

set critical_methodology [get_methodology_violations -quiet -filter {SEVERITY == "Critical Warning"}]
puts "CRITICAL_METHODOLOGY_COUNT|[llength $critical_methodology]"
if {[llength $critical_methodology] != 0} {
    foreach violation $critical_methodology {
        puts "CRITICAL_METHODOLOGY|[get_property ID $violation]"
    }
    error "Critical methodology violations remain"
}

set output_checkpoint [file join $output_dir "xc7z045_fabric_bist_routed_audited.dcp"]
write_checkpoint -force $output_checkpoint
puts "AUDITED_CHECKPOINT|$output_checkpoint"
puts "FABRIC_BIST_AUDIT_PASS|1"
close_design
exit 0
