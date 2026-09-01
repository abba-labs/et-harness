# Read-only XSDB discovery for one independently served JTAG chain.
set server_url "tcp:127.0.0.1:3121"
set role "observer"

if {[llength $argv] > 0} {
    set server_url [lindex $argv 0]
}
if {[llength $argv] > 1} {
    set role [lindex $argv 1]
}

set rc 0
set channel ""
puts "JTAG_DISCOVERY_START|role=$role|url=$server_url"

if {[catch {
    set channel [connect -url $server_url]
    puts "JTAG_CHANNEL|role=$role|channel=$channel"
    puts "JTAG_TARGETS_BEGIN|role=$role"
    puts [jtag targets]
    puts "JTAG_TARGETS_END|role=$role"
} error_message error_options]} {
    puts stderr "JTAG_DISCOVERY_ERROR|role=$role|message=$error_message"
    puts stderr "JTAG_DISCOVERY_ERROR_INFO|[dict get $error_options -errorinfo]"
    set rc 1
}

if {$channel ne ""} {
    catch {disconnect $channel}
}
puts "JTAG_DISCOVERY_END|role=$role|rc=$rc"
exit $rc
