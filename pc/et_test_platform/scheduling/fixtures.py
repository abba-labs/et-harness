# pytest 运行时 Fixture 与 Driver 构造入口。
#
# 职责：根据测试配置创建 Target/Driver/Capability/Bench 对象并提供可复用运行时事实。
# 边界：不隐式执行完整 Test Case，不拥有最终断言，也不把跨 IP 顺序藏入 Fixture。
# 依赖：依赖 pytest、各层稳定构造 API、Capability 和 Bench Loader。

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from ..core.errors import ConfigurationError
from ..drivers.framework import FrameworkDriver
from ..drivers.resource import RESOURCE_SERVICE_ID, ResourceDriver
from ..instruments.oscilloscopes import SignalObserver
from ..instruments.oscilloscopes.mso5204 import (
    Mso5204ObserverBinding,
    create_mso5204_signal_observer,
)
from ..instruments.signal_generators import PulseStimulus
from ..instruments.signal_generators.mso5204 import (
    Mso5204PulseBinding,
    create_mso5204_pulse_stimulus,
)
from ..profiles.bench import (
    load_debugger,
    load_pulse_stimulus,
    load_serial_target,
    load_signal_observer,
)
from ..profiles.capabilities import (
    ChipCapabilities,
    load_packaged_chip_capabilities,
)
from ..programmers import DebugController, JLinkDebugController
from .run_context import record_evidence, require_evidence
from .target_connection import create_serial_target_client
from .target_lifecycle import TargetLifecycleController


# 校验指定Service已由Framework发现；Registry未初始化时沿用FrameworkDriver的明确失败语义。
def _require_runtime_service(
    framework_communication: FrameworkDriver,
    service_id: int,
    instance_id: int,
    label: str,
) -> None:
    services = framework_communication.runtime_services
    if not any(
        item.service_id == service_id and item.instance_id == instance_id for item in services
    ):
        pytest.skip(
            f"skip_by_runtime_service: {label} service 0x{service_id:04x} "
            f"instance {instance_id} is not registered"
        )


def _require_hardware_gate(pytestconfig: pytest.Config) -> None:
    if not pytestconfig.getoption("et_hardware"):
        pytest.skip("real hardware requires explicit --et-hardware gate")


# 返回硬件 Case 的绝对产物目录；未开启硬件门或缺少目录参数时显式 Skip/UsageError。
@pytest.fixture
def et_artifact_dir(pytestconfig: pytest.Config) -> Path:

    _require_hardware_gate(pytestconfig)
    configured = pytestconfig.getoption("et_artifact_dir")
    if not configured:
        raise pytest.UsageError("--et-artifact-dir is required for hardware Case evidence")
    artifact_dir = Path(configured).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


# 建立 DUT 通信会话，校验 HELLO 身份并发现 Service；退出 Fixture 时始终关闭 Transport。
@pytest.fixture
def framework_communication(
    pytestconfig: pytest.Config,
    record_property: Callable[[str, object], None],
) -> Iterator[FrameworkDriver]:

    _require_hardware_gate(pytestconfig)
    bench = pytestconfig.getoption("et_bench")
    if not bench:
        raise pytest.UsageError("--et-bench is required for hardware Cases")

    target_name = pytestconfig.getoption("et_target")
    config = load_serial_target(bench, target_name)
    target = create_serial_target_client(config)
    target.open()
    try:
        driver = FrameworkDriver(target)
        hello = driver.hello()
        if hello.chip_id != config.chip_id:
            raise ConfigurationError(
                f"target {target_name!r} expected chip {config.chip_id!r}, "
                f"but HELLO reported {hello.chip_id!r}"
            )
        if (
            config.firmware_build_id is not None
            and hello.firmware_build_id != config.firmware_build_id
        ):
            raise ConfigurationError(
                f"target {target_name!r} expected firmware build "
                f"{config.firmware_build_id!r}, but HELLO reported "
                f"{hello.firmware_build_id!r}"
            )
        driver.discover_services()
        require_evidence(record_property, "dut")
        record_evidence(record_property, "dut")
        yield driver
    finally:
        target.close()


# 加载 HELLO 对应芯片的静态 Capability；运行时 Service Gate 由各 IP Support 负责。
@pytest.fixture
def target_capabilities(
    framework_communication: FrameworkDriver,
) -> ChipCapabilities:

    return load_packaged_chip_capabilities(framework_communication.chip_id)


# 确认 Resource Service 已注册后构造 Driver；服务缺失时按运行时能力显式 Skip。
@pytest.fixture
def resource_driver(framework_communication: FrameworkDriver) -> ResourceDriver:

    _require_runtime_service(
        framework_communication,
        RESOURCE_SERVICE_ID,
        0,
        "resource",
    )
    return ResourceDriver(framework_communication.target_client)


# 返回按逻辑信号构造外部示波器观测器的纯准备函数；构造阶段不打开仪器或发送命令。
@pytest.fixture
def signal_observer_for(pytestconfig: pytest.Config) -> Callable[[str], SignalObserver]:

    bench = pytestconfig.getoption("et_bench")
    if not bench:
        raise pytest.UsageError("--et-bench is required for signal observer Cases")
    target_name = pytestconfig.getoption("et_target")

    def build(logical_signal: str) -> SignalObserver:
        try:
            config = load_signal_observer(bench, target_name, logical_signal)
        except ConfigurationError as exc:
            pytest.skip(f"skip_by_bench_profile: {exc}")
        if config.driver.casefold() != "mso5204":
            pytest.skip(
                "skip_by_bench_profile: signal observer driver "
                f"{config.driver!r} has no registered adapter"
            )

        return create_mso5204_signal_observer(
            config.resource,
            Mso5204ObserverBinding(
                channel=config.channel,
                vertical_scale_v=config.vertical_scale_v,
                trigger_level_v=config.trigger_level_v,
                probe_ratio=config.probe_ratio,
            ),
            timeout_s=config.timeout_s,
        )

    return build


# 返回按逻辑名构造外部脉冲激励器的纯准备函数；不打开仪器或产生脉冲。
@pytest.fixture
def pulse_stimulus_for(pytestconfig: pytest.Config) -> Callable[[str], PulseStimulus]:

    bench = pytestconfig.getoption("et_bench")
    if not bench:
        raise pytest.UsageError("--et-bench is required for pulse stimulus Cases")
    target_name = pytestconfig.getoption("et_target")

    def build(logical_stimulus: str) -> PulseStimulus:
        try:
            config = load_pulse_stimulus(bench, target_name, logical_stimulus)
        except ConfigurationError as exc:
            pytest.skip(f"skip_by_bench_profile: {exc}")
        if config.driver.casefold() != "mso5204":
            pytest.skip(
                "skip_by_bench_profile: pulse stimulus driver "
                f"{config.driver!r} has no registered adapter"
            )

        return create_mso5204_pulse_stimulus(
            config.resource,
            Mso5204PulseBinding(
                output_channel=config.output_channel,
                amplitude_vpp=config.amplitude_vpp,
                offset_v=config.offset_v,
            ),
            timeout_s=config.timeout_s,
        )

    return build


# 构造预期复位后的通用Session重建控制器；Fixture本身不发送请求或改变目标状态。
@pytest.fixture
def target_lifecycle(
    framework_communication: FrameworkDriver,
) -> TargetLifecycleController:

    return TargetLifecycleController(framework_communication)


# 构造真实Debugger控制器；Fixture只解析配置和创建对象，不执行Halt/Resume。
@pytest.fixture
def debug_controller(
    pytestconfig: pytest.Config,
    et_artifact_dir: Path,
) -> DebugController:

    bench = pytestconfig.getoption("et_bench")
    if not bench:
        raise pytest.UsageError("--et-bench is required for debugger Cases")
    target_name = pytestconfig.getoption("et_target")
    # 缺工具配置属内部集成缺口，必须失败关闭；只有外部设备不可替代时才允许SKIP。
    try:
        config = load_debugger(bench, target_name)
    except ConfigurationError as exc:
        raise ConfigurationError(
            f"debugger binding is incomplete for target {target_name!r}: {exc}"
        ) from exc
    if config.driver.casefold() != "jlink":
        pytest.skip(
            f"skip_by_bench_profile: debugger driver {config.driver!r} has no registered adapter"
        )

    return JLinkDebugController(
        executable=config.executable,
        device=config.device,
        interface=config.interface,
        speed_khz=config.speed_khz,
        probe_serial=config.probe_serial,
        artifact_dir=et_artifact_dir,
        command_timeout_s=config.command_timeout_s,
    )
