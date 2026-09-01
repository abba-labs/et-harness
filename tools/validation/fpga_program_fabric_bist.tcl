# Volatile SRAM-only programming of the XC7Z045 Fabric BIST bitstream.

set bit_file [file normalize [lindex $argv 0]]
set property_log [file normalize [lindex $argv 1]]
set server_url "localhost:3121"
if {$argc >= 3} {
    set server_url [lindex $argv 2]
}
if {![file exists $bit_file]} {
    error "Bitstream not found: $bit_file"
}

open_hw_manager
puts "HW_SERVER_URL|$server_url"
connect_hw_server -url $server_url -allow_non_jtag
set targets [get_hw_targets -quiet *Digilent*]
if {[llength $targets] < 1} {
    error "No Digilent hardware target was found"
}
open_hw_target [lindex $targets 0]

set devices [get_hw_devices -quiet -filter {PART =~ "xc7z045*"}]
if {[llength $devices] != 1} {
    error "Expected exactly one xc7z045 device, found [llength $devices]"
}
set device [lindex $devices 0]
refresh_hw_device $device
set_property PROGRAM.FILE $bit_file $device
program_hw_devices $device
refresh_hw_device $device
report_property -all $device -file $property_log

puts "PROGRAMMED_DEVICE|[get_property PART $device]"
puts "PROGRAM_FILE|[get_property PROGRAM.FILE $device]"
if {![catch {get_property REGISTER.CONFIG_STATUS $device} config_status]} {
    puts "CONFIG_STATUS|$config_status"
}
puts "VOLATILE_SRAM_PROGRAM_PASS|1"

close_hw_target
disconnect_hw_server
close_hw_manager
exit 0
