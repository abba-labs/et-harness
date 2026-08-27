# Volatile PL SRAM programming only. Does not touch QSPI/flash/OTP/NVR.

set bit_file [file normalize [lindex $argv 0]]
set property_log [file normalize [lindex $argv 1]]
if {![file exists $bit_file]} { error "Bitstream not found: $bit_file" }
open_hw_manager
connect_hw_server -url localhost:3121 -allow_non_jtag
set targets [get_hw_targets -quiet *Digilent*]
if {[llength $targets] < 1} { error "No Digilent hardware target was found" }
open_hw_target [lindex $targets 0]
set devices [get_hw_devices -quiet -filter {PART =~ "xc7z045*"}]
if {[llength $devices] != 1} { error "Expected exactly one xc7z045 device" }
set device [lindex $devices 0]
refresh_hw_device $device
set_property PROGRAM.FILE $bit_file $device
program_hw_devices $device
refresh_hw_device $device
report_property -all $device -file $property_log
puts "PROGRAMMED_DEVICE|[get_property PART $device]"
puts "PROGRAM_FILE|[get_property PROGRAM.FILE $device]"
puts "OBSERVER_BIST_VOLATILE_PROGRAM_PASS|1"
close_hw_target
disconnect_hw_server
close_hw_manager
exit 0
