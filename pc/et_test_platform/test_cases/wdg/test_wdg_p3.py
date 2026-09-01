# WDG P3 Formal Case。
#
# 职责：验证真实Debugger Halt/Resume对WDG计数的暂停选择。
# 边界：不执行复位、烧录或芯片寄存器访问；调试器动作统一由公共Fixture提供。
# 依赖：WDG Driver、公共 DebugController、公共证据工具和pytest。

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ...drivers.crg import CrgPeripheral
from ...drivers.wdg import WdgConfig, WdgFeature
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ._support import WdgSupportFactory, require_wdg_runtime_feature

pytestmark = [pytest.mark.hardware, pytest.mark.ip("wdg")]

SAFE_RELOAD_COUNT = 100_000_000
DEBUG_HALT_WINDOW_S = 2.0
DEBUG_HALT_MAX_PAUSE_DELTA_RATIO = 0.25


# 测试 Feature：
# WDG Debug Halt暂停使能/失能以及CPU停止期间的计数行为。
#
# 测试方法：
# 1. 在reset输出关闭的独立模式下分别配置halt_pause_enable=True和False。
# 2. 两种配置使用相同Reload和相同Debugger Halt窗口，分别读取Halt前后的COUNTER.CURRENT。
# 3. 比较两轮Counter变化量，并保存真实Debugger日志和动作时间线。
#
# 通过条件：
# 1. halt_pause_enable=False时Counter明确推进。
# 2. halt_pause_enable=True时Counter变化不超过RUN_FREE路径的25%，且两次动作均有真实日志。
def test_wdg_p3_001_debugger_halt_behavior(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_id: int,
    debug_controller,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：只使用Runtime声明的Halt能力，复位输出关闭以保持Session在线。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.WDG, instance=wdg_instance_id)
    resource_driver.reset()

    support = wdg_support_for(wdg_instance_id)
    require_wdg_runtime_feature(support.runtime, WdgFeature.HALT_PAUSE)

    try:
        # 第一阶段：配置暂停使能并启动具有充足余量的WDG计数会话。
        support.wdg.unlock()
        support.wdg.disable()
        support.wdg.configure(
            WdgConfig(
                reload_count=SAFE_RELOAD_COUNT,
                reset_enable=False,
                halt_pause_enable=True,
            )
        )
        support.wdg.enable()

        # 激励：同一Debugger会话内完成Halt、固定保持和Resume。
        pause_before = support.wdg.status_get()
        pause_hold = debug_controller.hold_for(DEBUG_HALT_WINDOW_S)
        pause_after = support.wdg.status_get()
        pause_delta = max(0, pause_before.counter - pause_after.counter)

        # 第二阶段：关闭Halt暂停，使用同一Reload重建独立计数会话。
        support.wdg.disable()
        support.wdg.configure(
            WdgConfig(
                reload_count=SAFE_RELOAD_COUNT,
                reset_enable=False,
                halt_pause_enable=False,
            )
        )
        support.wdg.enable()

        # 激励：暂停失能时执行完全相同的Debugger Halt窗口。
        continue_before = support.wdg.status_get()
        continue_hold = debug_controller.hold_for(DEBUG_HALT_WINDOW_S)
        continue_after = support.wdg.status_get()
        continue_delta = max(0, continue_before.counter - continue_after.counter)

        # 证据：在决定性断言前保存真实Debugger时间线和Counter端点。
        record_property("debugger_identity", debug_controller.identity)
        record_property("halt_hold_s", DEBUG_HALT_WINDOW_S)
        record_property("pause_delta", pause_delta)
        record_property("run_free_delta", continue_delta)
        record_observation(
            record_property,
            key="pause_enabled_counter_samples",
            value=[pause_before.counter, pause_after.counter],
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_observation(
            record_property,
            key="pause_disabled_counter_samples",
            value=[continue_before.counter, continue_after.counter],
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_property(
            "expected_halt_behavior",
            {
                "pause_enabled": {
                    "maximum_run_free_ratio": DEBUG_HALT_MAX_PAUSE_DELTA_RATIO,
                },
                "pause_disabled": {"counter_advances": True},
            },
        )
        write_json_result(
            et_artifact_dir / "wdg_p3_001_debugger_halt_behavior.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p3_001",
                "debugger": {
                    "identity": debug_controller.identity,
                    "pause_hold": {
                        "action": pause_hold.action,
                        "requested_hold_s": pause_hold.requested_hold_s,
                        "started_s": pause_hold.started_s,
                        "completed_s": pause_hold.completed_s,
                        "stdout": str(pause_hold.stdout_path),
                        "stderr": str(pause_hold.stderr_path),
                    },
                    "continue_hold": {
                        "action": continue_hold.action,
                        "requested_hold_s": continue_hold.requested_hold_s,
                        "started_s": continue_hold.started_s,
                        "completed_s": continue_hold.completed_s,
                        "stdout": str(continue_hold.stdout_path),
                        "stderr": str(continue_hold.stderr_path),
                    },
                },
                "halt_hold_s": DEBUG_HALT_WINDOW_S,
                "counter": {
                    "pause_enabled_before": pause_before.counter,
                    "pause_enabled_after": pause_after.counter,
                    "pause_enabled_delta": pause_delta,
                    "pause_disabled_before": continue_before.counter,
                    "pause_disabled_after": continue_after.counter,
                    "pause_disabled_delta": continue_delta,
                },
            },
        )

        # 断言：RUN_FREE明确推进，PAUSE路径变化量显著小于RUN_FREE。
        assert continue_delta > 0
        assert pause_delta <= max(1, int(continue_delta * DEBUG_HALT_MAX_PAUSE_DELTA_RATIO))

    finally:
        # 清理：原子Halt动作已恢复CPU；这里只关闭WDG。
        support.wdg.disable()
