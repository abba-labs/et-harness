# Read-only Vivado LabTools scan of every target exposed by one hw_server.
set server_url "localhost:3121"
if {[llength $argv] > 0} {
    set server_url [lindex $argv 0]
}

set rc 0
open_hw_manager
if {[catch {
    connect_hw_server -url $server_url
    set targets [get_hw_targets]
    puts "HW_TARGET_COUNT=[llength $targets]"

    foreach target $targets {
        puts "HW_TARGET|url=$server_url|name=$target"
        if {[catch {open_hw_target $target} open_error]} {
            puts stderr "HW_TARGET_OPEN_ERROR|name=$target|message=$open_error"
            set rc 1
            continue
        }

        set devices [get_hw_devices]
        puts "HW_DEVICE_COUNT|target=$target|count=[llength $devices]"
        foreach device $devices {
            set part ""
            set idcode ""
            set ir_length ""
            catch {set part [get_property PART $device]}
            catch {set idcode [get_property IDCODE $device]}
            catch {set ir_length [get_property IR_LENGTH $device]}
            puts "HW_DEVICE|name=$device|part=$part|idcode=$idcode|ir_length=$ir_length"
        }
        close_hw_target $target
    }
} error_message error_options]} {
    puts stderr "HW_DEVICE_SCAN_ERROR|url=$server_url|message=$error_message"
    puts stderr "HW_DEVICE_SCAN_ERROR_INFO|[dict get $error_options -errorinfo]"
    set rc 1
}

catch {disconnect_hw_server}
close_hw_manager
exit $rc
