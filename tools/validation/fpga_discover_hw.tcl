# Non-destructive Vivado Hardware Manager discovery for the ET FPGA board.
# This script only enumerates the live JTAG chain. It does not program devices.

proc safe_property {name object} {
    if {[catch {get_property $name $object} value]} {
        return "<unavailable>"
    }
    if {$value eq ""} {
        return "<empty>"
    }
    return $value
}

set output_dir [file normalize [lindex $argv 0]]
file mkdir $output_dir
set report_path [file join $output_dir "jtag_devices.txt"]
set report [open $report_path "w"]

proc emit {channel message} {
    puts $message
    puts $channel $message
    flush $channel
}

set rc 0
emit $report "DISCOVERY_START|[clock format [clock seconds] -format {%Y-%m-%d %H:%M:%S}]"

if {[catch {
    open_hw_manager
    connect_hw_server -url localhost:3121
    set targets [get_hw_targets -quiet]
    emit $report "HW_TARGET_COUNT|[llength $targets]"

    foreach target $targets {
        current_hw_target $target
        if {[catch {open_hw_target} open_error]} {
            emit $report "HW_TARGET_OPEN_ERROR|$target|$open_error"
            continue
        }

        set devices [get_hw_devices -quiet]
        emit $report "HW_TARGET|$target|DEVICE_COUNT|[llength $devices]"
        foreach device $devices {
            emit $report "HW_DEVICE|NAME=[safe_property NAME $device]|PART=[safe_property PART $device]|IDCODE=[safe_property IDCODE $device]|PROGRAMMED=[safe_property PROGRAM.HW_CFGMEM_TYPE $device]"
        }
        close_hw_target
    }
} error_message error_options]} {
    emit $report "DISCOVERY_ERROR|$error_message"
    emit $report "DISCOVERY_ERROR_INFO|[dict get $error_options -errorinfo]"
    set rc 1
}

catch {disconnect_hw_server}
catch {close_hw_manager}
emit $report "DISCOVERY_END|RC=$rc"
close $report
exit $rc
