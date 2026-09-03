# STIMER停核观测映射与Case判据回归。
# 职责：验证映射和停核内取样语义，拒绝把PAUSE计数增长判为通过。
# 边界：只用测试替身，不连接探针或串口。
# 依赖：pytest、STIMER Case与芯片只读映射、Debugger结果模型。

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from et_test_platform.drivers.stimer import StimerFeature
from et_test_platform.programmers import DebugAction, HaltSamples
from et_test_platform.test_cases.stimer import conftest, test_stimer_p2


# 核对六个实例的CNT_RPT、STM_SET与Cortex-M7 DHCSR映射，不允许公共Case硬编码地址。
@pytest.mark.parametrize("instance", range(6))
def test_stimer_halt_mapping(instance):

    spec, mask = conftest.stimer_halt_mapping.__wrapped__(
        SimpleNamespace(chip_id="et6801"), instance
    )
    assert spec.status_address == 0xE000EDF0
    assert spec.halted_mask == 1 << 17
    assert spec.register_addresses == (
        0x40406068 + instance * 0x1000,
        0x40406004 + instance * 0x1000,
    )
    assert mask == 1 << 7


# 覆盖正确冻结、错误增长、自由运行不增长和策略配置错误；所有失败均先保存硬件事实。
@pytest.mark.parametrize(
    ("pause_end", "free_end", "pause_config", "passes"),
    [(100, 300, 3, True), (101, 300, 3, False), (100, 200, 3, False), (100, 300, 131, False)],
)
def test_stimer_halt_case_requires_frozen_count(
    tmp_path, monkeypatch, pause_end, free_end, pause_config, passes
):

    monkeypatch.setattr(test_stimer_p2.time, "sleep", lambda _: None)
    action = DebugAction("sample", 0, 1, tmp_path / "out.log", tmp_path / "err.log", 0.2)
    debugger = Mock(identity="test-probe")
    debugger.sample_while_halted.side_effect = [
        HaltSamples((100, pause_config), (pause_end, pause_config), (2,) * 4, 0, 0.2, action),
        HaltSamples((200, 131), (free_end, 131), (2,) * 4, 0, 0.2, action),
    ]
    driver = Mock()
    support = SimpleNamespace(
        stimer=driver,
        runtime=SimpleNamespace(
            features=(
                StimerFeature.DEBUG_HALT
                | StimerFeature.PERIOD
                | StimerFeature.START_STOP
                | StimerFeature.FREE_RUN
            ),
            maximum_period_ticks=0xFFFFFFFF,
        ),
    )
    properties = []
    arguments = dict(
        stimer_support_for=lambda _: support,
        stimer_instance_id=0,
        debug_controller=debugger,
        stimer_halt_mapping=(object(), 128),
        et_artifact_dir=tmp_path,
        record_property=lambda key, value: properties.append((key, value)),
        crg_driver=Mock(),
        resource_driver=Mock(),
    )
    if passes:
        test_stimer_p2.test_stimer_p2_003_debugger_halt_behavior(**arguments)
    else:
        with pytest.raises(AssertionError):
            test_stimer_p2.test_stimer_p2_003_debugger_halt_behavior(**arguments)

    assert debugger.sample_while_halted.call_count == 2
    driver.live_count_get.assert_not_called()
    assert dict(properties)["pause_delta"] == pause_end - 100
    assert (tmp_path / "stimer_p2_003_debugger_halt_behavior.json").is_file()
    assert driver.stop.call_count == 3
