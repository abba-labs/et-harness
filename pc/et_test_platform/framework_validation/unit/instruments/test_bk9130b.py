# B&K Precision 9130B 无硬件协议单元测试。
#
# 职责：验证原子 API 的 SCPI 映射、关键响应解析、范围校验和手册 API Inventory。
# 边界：只验证软件命令契约，不模拟或证明真实 9130B 硬件行为。
# 依赖：仅依赖 9130B Driver、公共 ScpiSession 和测试内 ScriptedTransport。

from __future__ import annotations

from collections import deque

import pytest

from et_test_platform.communication.transport import ByteTransport
from et_test_platform.instruments.common.scpi import ScpiSession
from et_test_platform.instruments.power_supplies.bk9130b.driver import Bk9130bDriver
from et_test_platform.instruments.power_supplies.bk9130b.models import Bk9130bChannel
from et_test_platform.instruments.power_supplies.bk9130b.operations import (
    all_outputs_off,
    configure_channel_and_enable,
)


# 提供测试内可脚本化字节 Transport；不模拟真实仪器时序或电源输出。
class ScriptedTransport(ByteTransport):
    def __init__(self, responses: dict[bytes, bytes] | None = None) -> None:
        self.responses = responses or {}
        self.writes: list[bytes] = []
        self._pending = deque[bytes]()

    @property
    def identity(self) -> str:
        return "scripted:bk9130b"

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def write(self, data: bytes, *, timeout_s: float | None = None) -> None:
        self.writes.append(data)
        response = self.responses.get(data)
        if response is not None:
            self._pending.append(response)

    def read(self, max_bytes: int, timeout_s: float | None = None) -> bytes:
        if not self._pending:
            return b""
        current = self._pending.popleft()
        if len(current) <= max_bytes:
            return current
        self._pending.appendleft(current[max_bytes:])
        return current[:max_bytes]


def _driver(
    responses: dict[bytes, bytes] | None = None,
) -> tuple[Bk9130bDriver, ScriptedTransport]:
    transport = ScriptedTransport(responses)
    return Bk9130bDriver(ScpiSession(transport)), transport


def _public_methods(control: object) -> set[str]:
    return {
        name
        for name in dir(control)
        if not name.startswith("_") and callable(getattr(control, name))
    }


# 验证 IEEE488.2 和系统 API 保持一条方法只发送一条命令。
def test_common_and_system_mapping() -> None:
    responses = {
        b"*IDN?\n": b"B&K Precision,9130B,123456,V1.06-V1.04\n",
        b"SYSTem:ERRor?\n": b'-113,"Undefined header"\n',
        b"SYSTem:COMMunicate:GPIB:RDEVice:ADDRess?\n": b"9\n",
    }
    driver, transport = _driver(responses)

    driver.common.clear_status()
    driver.common.event_status_enable_set(128)
    assert driver.common.identity_get().model == "9130B"
    assert driver.system.error_get().code == -113
    driver.system.gpib_address_set(9)
    assert driver.system.gpib_address_get() == 9

    assert transport.writes == [
        b"*CLS\n",
        b"*ESE 128\n",
        b"*IDN?\n",
        b"SYSTem:ERRor?\n",
        b"SYSTem:COMMunicate:GPIB:RDEVice:ADDRess 9\n",
        b"SYSTem:COMMunicate:GPIB:RDEVice:ADDRess?\n",
    ]


# 验证 Source、Output 和 OVP 方法不会隐式切换通道或追加额外命令。
def test_source_and_output_mapping() -> None:
    responses = {
        b"VOLTage:LEVel?\n": b"12.0\n",
        b"CURRent:LEVel?\n": b"1.5\n",
        b"VOLTage:PROTection:TRIPed?\n": b"0\n",
        b"OUTPut:STATe?\n": b"1\n",
    }
    driver, transport = _driver(responses)

    driver.source.voltage_set(12.0)
    driver.source.current_set(1.5)
    assert driver.source.voltage_get() == pytest.approx(12.0)
    assert driver.source.current_get() == pytest.approx(1.5)
    driver.source.voltage_protection_level_set(15.0)
    assert driver.source.voltage_protection_tripped_get() is False
    driver.output.enabled_set(True)
    assert driver.output.enabled_get() is True

    assert transport.writes == [
        b"VOLTage:LEVel 12\n",
        b"CURRent:LEVel 1.5\n",
        b"VOLTage:LEVel?\n",
        b"CURRent:LEVel?\n",
        b"VOLTage:PROTection:LEVel 15\n",
        b"VOLTage:PROTection:TRIPed?\n",
        b"OUTPut:STATe ON\n",
        b"OUTPut:STATe?\n",
    ]


# 验证通道选择、组合和触发耦合都保持独立原子命令。
def test_channel_and_trigger_mapping() -> None:
    responses = {
        b"INSTrument:SELect?\n": b"CH2\n",
        b"INSTrument:COUPle:TRIGger?\n": b"CH1,CH3\n",
        b"TRIGger:DELay?\n": b"0.5\n",
    }
    driver, transport = _driver(responses)

    driver.channel.select_set(Bk9130bChannel.CH2)
    assert driver.channel.select_get() is Bk9130bChannel.CH2
    driver.channel.combine_series_set((Bk9130bChannel.CH1, Bk9130bChannel.CH2))
    driver.channel.combine_parallel_set(None)
    driver.channel.couple_trigger_set((Bk9130bChannel.CH1, Bk9130bChannel.CH3))
    assert driver.channel.couple_trigger_get() == (Bk9130bChannel.CH1, Bk9130bChannel.CH3)
    driver.trigger.delay_set(0.5)
    assert driver.trigger.delay_get() == pytest.approx(0.5)

    assert transport.writes == [
        b"INSTrument:SELect CH2\n",
        b"INSTrument:SELect?\n",
        b"INSTrument:COMbine:SERies CH1,CH2\n",
        b"INSTrument:COMbine:PARAllel NONE\n",
        b"INSTrument:COUPle:TRIGger CH1,CH3\n",
        b"INSTrument:COUPle:TRIGger?\n",
        b"TRIGger:DELay 0.5\n",
        b"TRIGger:DELay?\n",
    ]


# 验证 APPLy 单条命令支持通道专用范围，并正确解析三通道响应。
def test_apply_mapping_and_channel_limits() -> None:
    responses = {
        b"APPLy? CH3\n": b"5.0,2.0\n",
        b"APPLy:VOLTage?\n": b"3.0,4.0,5.0\n",
        b"APPLy:OUTput?\n": b"1,0,1\n",
    }
    driver, transport = _driver(responses)

    driver.apply.channel_set(Bk9130bChannel.CH3, 5.0, 2.0)
    assert driver.apply.channel_get(Bk9130bChannel.CH3).current_a == pytest.approx(2.0)
    assert driver.apply.voltages_get() == pytest.approx((3.0, 4.0, 5.0))
    assert driver.apply.outputs_get() == (True, False, True)
    with pytest.raises(ValueError):
        driver.apply.channel_set(Bk9130bChannel.CH3, 5.1, 1.0)

    assert transport.writes == [
        b"APPLy CH3,5,2\n",
        b"APPLy? CH3\n",
        b"APPLy:VOLTage?\n",
        b"APPLy:OUTput?\n",
    ]


# 验证状态寄存器 API 使用正确的 QUEStionable/OPERation 和通道汇总路径。
def test_status_mapping() -> None:
    responses = {
        b"STATus:QUEStionable:EVENt?\n": b"3\n",
        b"STATus:QUEStionable:INSTrument:ISUMmary2:CONDition?\n": b"1\n",
        b"STATus:OPERation:INSTrument:ISUMmary3:ENABle?\n": b"7\n",
    }
    driver, transport = _driver(responses)

    assert driver.status.questionable_event_get() == 3
    driver.status.questionable_summary1_enable_set(5)
    assert driver.status.questionable_summary2_condition_get() == 1
    driver.status.operation_summary3_enable_set(7)
    assert driver.status.operation_summary3_enable_get() == 7

    assert transport.writes == [
        b"STATus:QUEStionable:EVENt?\n",
        b"STATus:QUEStionable:INSTrument:ISUMmary1:ENABle 5\n",
        b"STATus:QUEStionable:INSTrument:ISUMmary2:CONDition?\n",
        b"STATus:OPERation:INSTrument:ISUMmary3:ENABle 7\n",
        b"STATus:OPERation:INSTrument:ISUMmary3:ENABle?\n",
    ]


# 验证组合操作只按可见顺序复用公开原子 API，不把隐藏行为塞入 Driver。
def test_operations_compose_atomic_calls() -> None:
    driver, transport = _driver()

    configure_channel_and_enable(driver, Bk9130bChannel.CH1, 5.0, 1.0)
    all_outputs_off(driver)

    assert transport.writes == [
        b"INSTrument:SELect CH1\n",
        b"VOLTage:LEVel 5\n",
        b"CURRent:LEVel 1\n",
        b"CHANnel:OUTPut:STATe ON\n",
        b"APPLy:OUTput 0,0,0\n",
    ]


# 固化编程手册详细命令章节的 136 个稳定原子语义，防止重构静默删减控制能力。
def test_bk9130b_public_api_inventory_matches_detailed_manual() -> None:
    expected = {
        "common": {
            "clear_status",
            "event_status_enable_set",
            "event_status_enable_get",
            "event_status_register_get",
            "identity_get",
            "operation_complete",
            "operation_complete_get",
            "reset",
            "service_request_enable_set",
            "service_request_enable_get",
            "status_byte_get",
            "trigger",
            "state_save",
            "state_recall",
            "self_test_get",
            "wait",
            "power_on_status_clear_set",
            "power_on_status_clear_get",
        },
        "system": {
            "error_get",
            "version_get",
            "remote",
            "local",
            "remote_write_lock",
            "gpib_address_set",
            "gpib_address_get",
            "beep",
            "interface_set",
            "memory_group_set",
            "memory_group_get",
        },
        "status": {
            "preset",
            "questionable_event_get",
            "questionable_condition_get",
            "questionable_enable_set",
            "questionable_enable_get",
            "questionable_instrument_event_get",
            "questionable_instrument_enable_set",
            "questionable_instrument_enable_get",
            "questionable_summary1_event_get",
            "questionable_summary1_enable_set",
            "questionable_summary1_enable_get",
            "questionable_summary1_condition_get",
            "questionable_summary2_event_get",
            "questionable_summary2_enable_set",
            "questionable_summary2_enable_get",
            "questionable_summary2_condition_get",
            "questionable_summary3_event_get",
            "questionable_summary3_enable_set",
            "questionable_summary3_enable_get",
            "questionable_summary3_condition_get",
            "operation_event_get",
            "operation_condition_get",
            "operation_enable_set",
            "operation_enable_get",
            "operation_instrument_event_get",
            "operation_instrument_enable_set",
            "operation_instrument_enable_get",
            "operation_summary1_event_get",
            "operation_summary1_enable_set",
            "operation_summary1_enable_get",
            "operation_summary1_condition_get",
            "operation_summary2_event_get",
            "operation_summary2_enable_set",
            "operation_summary2_enable_get",
            "operation_summary2_condition_get",
            "operation_summary3_event_get",
            "operation_summary3_enable_set",
            "operation_summary3_enable_get",
            "operation_summary3_condition_get",
        },
        "output": {
            "enabled_set",
            "enabled_get",
            "timer_enabled_set",
            "timer_enabled_get",
            "timer_delay_set",
            "timer_data_get",
            "tracking_enabled_set",
            "tracking_enabled_get",
            "series_enabled_set",
            "series_enabled_get",
            "parallel_enabled_set",
            "parallel_enabled_get",
        },
        "source": {
            "channel_output_enabled_set",
            "channel_output_enabled_get",
            "current_set",
            "current_get",
            "current_up",
            "current_down",
            "current_step_set",
            "current_step_get",
            "current_triggered_set",
            "current_triggered_get",
            "voltage_set",
            "voltage_get",
            "voltage_up",
            "voltage_down",
            "voltage_step_set",
            "voltage_step_get",
            "voltage_triggered_set",
            "voltage_triggered_get",
            "voltage_protection_enabled_set",
            "voltage_protection_enabled_get",
            "voltage_protection_level_set",
            "voltage_protection_level_get",
            "voltage_protection_tripped_get",
            "voltage_protection_clear",
            "voltage_limit_set",
            "voltage_limit_get",
        },
        "display": {"enabled_set", "enabled_get", "text_set", "text_get", "text_clear"},
        "trigger": {"immediate", "delay_set", "delay_get"},
        "channel": {
            "select_set",
            "select_get",
            "number_set",
            "number_get",
            "combine_series_set",
            "combine_parallel_set",
            "combine_tracking_set",
            "couple_trigger_set",
            "couple_trigger_get",
        },
        "measurement": {
            "voltage_get",
            "current_get",
            "power_get",
            "all_currents_get",
            "all_voltages_get",
        },
        "apply": {
            "channel_set",
            "channel_get",
            "voltages_set",
            "voltages_get",
            "currents_set",
            "currents_get",
            "outputs_set",
            "outputs_get",
        },
    }
    driver, _ = _driver()
    assert sum(len(methods) for methods in expected.values()) == 136
    for group, methods in expected.items():
        assert _public_methods(getattr(driver, group)) == methods
