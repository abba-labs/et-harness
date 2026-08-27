# Repeated volatile PL-SRAM programming and sanitized configuration checks.

set bit_file [file normalize [lindex $argv 0]]
set iterations [lindex $argv 1]
if {$iterations eq ""} { set iterations 5 }
if {![file exists $bit_file]} { error "Bitstream not found: $bit_file" }

proc checked_property {device property expected} {
    if {[catch {get_property $property $device} value]} {
        error "Required property unavailable: $property"
    }
    if {$value ne $expected} {
        error "Property $property expected $expected, got $value"
    }
    return $value
}

open_hw_manager
connect_hw_server -url localhost:3121 -allow_non_jtag
set targets [get_hw_targets -quiet *Digilent*]
if {[llength $targets] < 1} { error "No Digilent hardware target was found" }
open_hw_target [lindex $targets 0]

set devices [get_hw_devices -quiet -filter {PART =~ "xc7z045*"}]
if {[llength $devices] != 1} {
    error "Expected exactly one xc7z045 device, found [llength $devices]"
}
set device [lindex $devices 0]
set_property PROGRAM.FILE $bit_file $device

for {set iteration 1} {$iteration <= $iterations} {incr iteration} {
    program_hw_devices $device
    refresh_hw_device $device

    checked_property $device IDCODE_HEX 23731093
    checked_property $device REGISTER.CONFIG_STATUS.BIT00_CRC_ERROR 0
    checked_property $device REGISTER.CONFIG_STATUS.BIT02_PLL_LOCK_STATUS 1
    checked_property $device REGISTER.CONFIG_STATUS.BIT04_END_OF_STARTUP_\(EOS\)_STATUS 1
    checked_property $device REGISTER.CONFIG_STATUS.BIT13_DONE_INTERNAL_SIGNAL_STATUS 1
    checked_property $device REGISTER.CONFIG_STATUS.BIT14_DONE_PIN 1
    checked_property $device REGISTER.CONFIG_STATUS.BIT15_IDCODE_ERROR 0
    checked_property $device REGISTER.CONFIG_STATUS.BIT16_SECURITY_ERROR 0
    checked_property $device REGISTER.CONFIG_STATUS.BIT17_SYSTEM_MONITOR_OVER-TEMP_ALARM_STATUS 0
    checked_property $device REGISTER.CONFIG_STATUS.BIT27_HMAC_ERROR 0
    checked_property $device REGISTER.CONFIG_STATUS.BIT29_BAD_PACKET_ERROR 0

    puts "REPROGRAM_ITERATION|$iteration|PASS"
    after 100
}

puts "REPROGRAM_COUNT|$iterations"
puts "REPEATED_VOLATILE_PROGRAM_PASS|1"
close_hw_target
disconnect_hw_server
close_hw_manager
exit 0
