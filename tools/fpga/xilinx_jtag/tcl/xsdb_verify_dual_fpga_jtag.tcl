# Read-only verification of the observer and DUT JTAG servers.
# Both channels remain connected until both target lists have been captured.
set observer_url "tcp:127.0.0.1:3121"
set dut_url "tcp:127.0.0.1:3122"

if {[llength $argv] > 0} {
    set observer_url [lindex $argv 0]
}
if {[llength $argv] > 1} {
    set dut_url [lindex $argv 1]
}

set observer_channel ""
set dut_channel ""
set rc 0

puts "DUAL_JTAG_VERIFY_START|observer=$observer_url|dut=$dut_url"
if {[catch {
    set observer_channel [connect -url $observer_url]
    set observer_targets [jtag targets]
    puts "JTAG_CHANNEL|role=observer|channel=$observer_channel"

    set dut_channel [connect -url $dut_url]
    set dut_targets [jtag targets]
    puts "JTAG_CHANNEL|role=dut|channel=$dut_channel"

    puts "JTAG_TARGETS_BEGIN|role=observer"
    puts $observer_targets
    puts "JTAG_TARGETS_END|role=observer"
    puts "JTAG_TARGETS_BEGIN|role=dut"
    puts $dut_targets
    puts "JTAG_TARGETS_END|role=dut"
} error_message error_options]} {
    puts stderr "DUAL_JTAG_VERIFY_ERROR|message=$error_message"
    puts stderr "DUAL_JTAG_VERIFY_ERROR_INFO|[dict get $error_options -errorinfo]"
    set rc 1
}

if {$dut_channel ne ""} {
    catch {disconnect $dut_channel}
}
if {$observer_channel ne ""} {
    catch {disconnect $observer_channel}
}
puts "DUAL_JTAG_VERIFY_END|rc=$rc"
exit $rc
