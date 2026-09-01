# Read the configured XC7Z045 SRAM twice without capture or run-control side effects.

set output_dir [file normalize [lindex $argv 0]]
file mkdir $output_dir
set readback_1 [file join $output_dir "configuration_readback_1.bin"]
set readback_2 [file join $output_dir "configuration_readback_2.bin"]

open_hw_manager
connect_hw_server -url localhost:3121 -allow_non_jtag
set targets [get_hw_targets -quiet *Digilent*]
if {[llength $targets] < 1} { error "No Digilent hardware target was found" }
open_hw_target [lindex $targets 0]
set devices [get_hw_devices -quiet -filter {PART =~ "xc7z045*"}]
if {[llength $devices] != 1} { error "Expected exactly one xc7z045 device" }
set device [lindex $devices 0]
refresh_hw_device $device

readback_hw_device -force -bin_file $readback_1 $device
after 100
readback_hw_device -force -bin_file $readback_2 $device

foreach path [list $readback_1 $readback_2] {
    if {![file exists $path] || [file size $path] == 0} {
        error "Configuration readback file missing or empty: $path"
    }
}
refresh_hw_device $device
if {[get_property REGISTER.CONFIG_STATUS.BIT00_CRC_ERROR $device] ne "0"} {
    error "CRC error asserted after configuration readback"
}
if {[get_property REGISTER.CONFIG_STATUS.BIT14_DONE_PIN $device] ne "1"} {
    error "DONE pin deasserted after configuration readback"
}

puts "READBACK_FILE_1|$readback_1|BYTES=[file size $readback_1]"
puts "READBACK_FILE_2|$readback_2|BYTES=[file size $readback_2]"
puts "CONFIGURATION_READBACK_PASS|1"
close_hw_target
disconnect_hw_server
close_hw_manager
exit 0
