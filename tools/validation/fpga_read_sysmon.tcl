# Read sanitized on-chip XADC/System Monitor telemetry through JTAG.

proc get_required_numeric {object property} {
    if {[catch {get_property $property $object} value]} {
        error "Required SysMon property unavailable: $property"
    }
    if {![string is double -strict $value]} {
        error "SysMon property $property is not numeric: $value"
    }
    return $value
}

set output_file [file normalize [lindex $argv 0]]
set report [open $output_file "w"]
proc emit {channel message} {
    puts $message
    puts $channel $message
    flush $channel
}

open_hw_manager
connect_hw_server -url localhost:3121 -allow_non_jtag
set targets [get_hw_targets -quiet *Digilent*]
if {[llength $targets] < 1} { error "No Digilent hardware target was found" }
open_hw_target [lindex $targets 0]
set devices [get_hw_devices -quiet -filter {PART =~ "xc7z045*"}]
if {[llength $devices] != 1} { error "Expected exactly one xc7z045 device" }
set device [lindex $devices 0]
refresh_hw_device $device

if {[get_property IS_SYSMON_SUPPORTED $device] ne "1"} {
    error "XC7Z045 hardware target does not expose SysMon support"
}
set sysmons [get_hw_sysmons -quiet -of_objects $device]
if {[llength $sysmons] < 1} { error "No SysMon object was created" }
set sysmon [lindex $sysmons 0]
refresh_hw_sysmon -properties {TEMPERATURE VCCINT VCCAUX VCCBRAM} $sysmon

set temperature [get_required_numeric $sysmon TEMPERATURE]
set vccint [get_required_numeric $sysmon VCCINT]
set vccaux [get_required_numeric $sysmon VCCAUX]
set vccbram [get_required_numeric $sysmon VCCBRAM]

emit $report "SYSMON_TEMPERATURE_C|$temperature"
emit $report "SYSMON_VCCINT_V|$vccint"
emit $report "SYSMON_VCCAUX_V|$vccaux"
emit $report "SYSMON_VCCBRAM_V|$vccbram"

if {$temperature < -40.0 || $temperature > 125.0} { error "Temperature outside sanity range" }
if {$vccint < 0.80 || $vccint > 1.20} { error "VCCINT outside sanity range" }
if {$vccaux < 1.60 || $vccaux > 2.00} { error "VCCAUX outside sanity range" }
if {$vccbram < 0.80 || $vccbram > 1.20} { error "VCCBRAM outside sanity range" }

emit $report "SYSMON_JTAG_READ_PASS|1"
close $report
close_hw_target
disconnect_hw_server
close_hw_manager
exit 0
