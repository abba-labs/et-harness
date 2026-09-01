# Synthesize the XC7Z045 Observer BIST and stop before implementation so the
# next stage can run in a fresh process under the 2048 MB process limit.

set output_dir [file normalize [lindex $argv 0]]
file mkdir $output_dir
set script_dir [file dirname [file normalize [info script]]]
set project_root [file normalize [file join $script_dir ".." ".." ".."]]
set rtl_file [file join $project_root "workspaces" "xc7z045_observer_bist" "rtl" "xc7z045_observer_bist.v"]
set xdc_file [file join $project_root "workspaces" "xc7z045_observer_bist" "constraints" "xc7z045_observer_bist.xdc"]
set target_part "xc7z045ffg900-2"

if {[llength [get_parts -quiet $target_part]] != 1} { error "Required part is missing" }
# Single-thread synthesis reduces temporary disk pressure on this guarded host.
set_param general.maxThreads 1
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
if {$iobuf_count != 12 || $bram_count < 2} { error "Required IO/BRAM resources were not retained" }

report_utilization -hierarchical -file [file join $output_dir "utilization_synth.rpt"]
set checkpoint [file join $output_dir "xc7z045_observer_bist_synth.dcp"]
write_checkpoint -force $checkpoint
puts "SYNTH_CHECKPOINT|$checkpoint"
puts "OBSERVER_BIST_SYNTH_PASS|1"
close_design
exit 0
