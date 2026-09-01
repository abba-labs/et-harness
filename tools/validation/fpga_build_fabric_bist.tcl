# Build the XC7Z045 internal Fabric BIST bitstream. No external user IO is used.

set output_dir [file normalize [lindex $argv 0]]
file mkdir $output_dir

set script_dir [file dirname [file normalize [info script]]]
set project_root [file normalize [file join $script_dir ".." ".." ".."]]
set rtl_file [file join $project_root "workspaces" "xc7z045_fabric_bist" "rtl" "xc7z045_fabric_bist.v"]
set xdc_file [file join $project_root "workspaces" "xc7z045_fabric_bist" "constraints" "xc7z045_fabric_bist.xdc"]
set target_part "xc7z045ffg900-2"

set matching_parts [get_parts -quiet $target_part]
if {[llength $matching_parts] != 1} {
    error "Required Vivado part is not installed: $target_part"
}

create_project -force xc7z045_fabric_bist [file join $output_dir "vivado_project"] -part $target_part
set_property target_language Verilog [current_project]
add_files -norecurse $rtl_file
add_files -fileset constrs_1 -norecurse $xdc_file
set_property top xc7z045_fabric_bist [current_fileset]
update_compile_order -fileset sources_1

launch_runs synth_1 -jobs 2
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "SYNTH_STATUS|$synth_status"
if {![string match "*Complete*" $synth_status]} {
    error "Synthesis failed: $synth_status"
}

open_run synth_1
set synth_dsp_count [llength [get_cells -hierarchical -filter {REF_NAME =~ DSP48*}]]
set synth_bram_count [llength [get_cells -hierarchical -filter {REF_NAME =~ RAMB36*}]]
set synth_lut_count [llength [get_cells -hierarchical -filter {REF_NAME =~ LUT*}]]
set synth_ff_count [llength [get_cells -hierarchical -filter {REF_NAME =~ FD*}]]
puts "SYNTH_RESOURCES|DSP48=$synth_dsp_count|RAMB36=$synth_bram_count|LUT=$synth_lut_count|FF=$synth_ff_count"
if {$synth_dsp_count < 1} {
    error "Fabric BIST did not retain a DSP48 resource"
}
if {$synth_bram_count < 4} {
    error "Fabric BIST did not retain at least four RAMB36 resources"
}
close_design

launch_runs impl_1 -to_step write_bitstream -jobs 2
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "IMPL_STATUS|$impl_status"
if {![string match "*Complete*" $impl_status]} {
    error "Implementation or bitstream generation failed: $impl_status"
}

open_run impl_1
report_drc -file [file join $output_dir "drc.rpt"]
report_timing_summary -file [file join $output_dir "timing_summary.rpt"]
report_utilization -hierarchical -file [file join $output_dir "utilization_hierarchical.rpt"]
report_methodology -file [file join $output_dir "methodology.rpt"]
write_checkpoint -force [file join $output_dir "xc7z045_fabric_bist_routed.dcp"]

set worst_path [get_timing_paths -max_paths 1 -nworst 1]
if {[llength $worst_path] > 0} {
    set worst_slack [get_property SLACK $worst_path]
    puts "WORST_SLACK_NS|$worst_slack"
    if {$worst_slack < 0.0} {
        error "Timing failed with slack $worst_slack ns"
    }
}

set run_dir [get_property DIRECTORY [get_runs impl_1]]
set generated_bit [file join $run_dir "xc7z045_fabric_bist.bit"]
set output_bit [file join $output_dir "xc7z045_fabric_bist.bit"]
if {![file exists $generated_bit]} {
    error "Generated bitstream not found: $generated_bit"
}
file copy -force $generated_bit $output_bit

puts "TARGET_PART|$target_part"
puts "OUTPUT_BIT|$output_bit"
puts "FABRIC_BIST_BUILD_PASS|1"
close_project
exit 0
