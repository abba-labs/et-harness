# Synthesize, optimize, and place the XC7Z045 JTAG-only Observer BIST.

set output_dir [file normalize [lindex $argv 0]]
file mkdir $output_dir
set script_dir [file dirname [file normalize [info script]]]
set project_root [file normalize [file join $script_dir ".." ".." ".."]]
set rtl_file [file join $project_root "workspaces" "xc7z045_observer_bist" "rtl" "xc7z045_observer_bist.v"]
set xdc_file [file join $project_root "workspaces" "xc7z045_observer_bist" "constraints" "xc7z045_observer_bist.xdc"]
set target_part "xc7z045ffg900-2"

if {[llength [get_parts -quiet $target_part]] != 1} {
    error "Required Vivado part is not installed: $target_part"
}
set_param general.maxThreads 2
read_verilog $rtl_file
read_xdc $xdc_file
synth_design -top xc7z045_observer_bist -part $target_part

set iobuf_count [llength [get_cells -hierarchical -filter {REF_NAME == IOBUF}]]
set bram_count [expr {
    [llength [get_cells -hierarchical -filter {REF_NAME =~ RAMB36*}]] +
    [llength [get_cells -hierarchical -filter {REF_NAME =~ RAMB18*}]]
}]
set lut_count [llength [get_cells -hierarchical -filter {REF_NAME =~ LUT*}]]
set ff_count [llength [get_cells -hierarchical -filter {REF_NAME =~ FD*}]]
puts "SYNTH_RESOURCES|IOBUF=$iobuf_count|BRAM_PRIMITIVES=$bram_count|LUT=$lut_count|FF=$ff_count"
if {$iobuf_count != 12} {
    error "Expected 12 IOBUF instances, found $iobuf_count"
}
if {$bram_count < 2} {
    error "Observer BIST did not retain enough BRAM resources"
}

opt_design
place_design -directive Quick
phys_opt_design -directive AddRetime
report_io -file [file join $output_dir "observer_io_placed.rpt"]
report_utilization -hierarchical -file [file join $output_dir "utilization_placed.rpt"]
report_timing_summary -file [file join $output_dir "timing_placed.rpt"]
write_checkpoint -force [file join $output_dir "xc7z045_observer_bist_placed.dcp"]

puts "PLACED_CHECKPOINT|[file join $output_dir xc7z045_observer_bist_placed.dcp]"
puts "OBSERVER_BIST_PLACE_PASS|1"
close_design
exit 0
