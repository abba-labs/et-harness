if {[llength $argv] != 3} {
    error "Usage: program_xc7vx980t.tcl <bitfile> <server_url> <property_output>"
}

set bitfile [file normalize [lindex $argv 0]]
set server_url [lindex $argv 1]
set property_output [file normalize [lindex $argv 2]]

if {![file exists $bitfile]} {
    error "Bitfile not found: $bitfile"
}

proc require_property {device property expected} {
    set actual [get_property $property $device]
    puts "CONFIG_CHECK|property=$property|expected=$expected|actual=$actual"
    if {$actual ne $expected} {
        error "Configuration property $property expected $expected, got $actual"
    }
}

open_hw_manager
connect_hw_server -url $server_url

set targets [get_hw_targets]
if {[llength $targets] != 1} {
    error "Expected exactly one hardware target on $server_url, found [llength $targets]"
}

set target [lindex $targets 0]
puts "HW_TARGET|name=[get_property NAME $target]"
set_property PARAM.FREQUENCY 3000000 $target
open_hw_target $target

set matches {}
foreach device [get_hw_devices] {
    set part [string tolower [get_property PART $device]]
    set name [get_property NAME $device]
    puts "HW_DEVICE|name=$name|part=$part"
    if {[string match "xc7z045*" $part]} {
        error "Refusing XC7Z045 route while targeting XC7VX980T"
    }
    if {[string match "xc7vx980t*" $part]} {
        lappend matches $device
    }
}

if {[llength $matches] != 1} {
    error "Expected exactly one XC7VX980T on $server_url, found [llength $matches]"
}

set device [lindex $matches 0]
set_property PROGRAM.FILE $bitfile $device

puts "PROGRAM_START|device=[get_property NAME $device]|part=[get_property PART $device]|bit=$bitfile"
program_hw_devices $device
refresh_hw_device -update_hw_probes false $device

require_property $device REGISTER.CONFIG_STATUS.BIT00_CRC_ERROR 0
require_property $device REGISTER.CONFIG_STATUS.BIT04_END_OF_STARTUP_\(EOS\)_STATUS 1
require_property $device REGISTER.CONFIG_STATUS.BIT13_DONE_INTERNAL_SIGNAL_STATUS 1
require_property $device REGISTER.CONFIG_STATUS.BIT14_DONE_PIN 1
require_property $device REGISTER.CONFIG_STATUS.BIT15_IDCODE_ERROR 0
require_property $device REGISTER.CONFIG_STATUS.BIT16_SECURITY_ERROR 0

set channel [open $property_output w]
foreach property [lsort [list_property $device]] {
    if {[string match "REGISTER.*" $property] ||
        $property eq "NAME" ||
        $property eq "PART" ||
        $property eq "PROGRAM.FILE"} {
        if {![catch {get_property $property $device} value]} {
            puts $channel "$property=$value"
        }
    }
}
close $channel

puts "XC7VX980T_VOLATILE_PROGRAM_PASS|device=[get_property NAME $device]|part=[get_property PART $device]"

close_hw_target
disconnect_hw_server
close_hw_manager
exit 0
