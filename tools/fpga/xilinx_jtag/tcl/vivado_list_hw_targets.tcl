# Read-only Vivado LabTools listing for one hw_server.
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
        puts "HW_TARGET|url=$server_url|name=[get_property NAME $target]"
    }
} error_message error_options]} {
    puts stderr "HW_TARGET_LIST_ERROR|url=$server_url|message=$error_message"
    puts stderr "HW_TARGET_LIST_ERROR_INFO|[dict get $error_options -errorinfo]"
    set rc 1
}

catch {disconnect_hw_server}
close_hw_manager
exit $rc
