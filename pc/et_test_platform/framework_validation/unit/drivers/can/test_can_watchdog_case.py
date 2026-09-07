# CAN Watchdog基础Case的软件回归。
# 职责：真实Driver/Codec运行三阶段，独立注入WDI、ISR、清除、数据及计数坏值。
# 边界：替身不模拟RAM握手延迟，不形成硬件PASS。
# 依赖：真实Case、严格命令白名单及显式DMA/Resource/STIMER替身。

from dataclasses import replace
from struct import pack, unpack
from types import SimpleNamespace

import pytest
from et_test_platform.core.errors import RequestTimeout
from et_test_platform.drivers.can import CanDriver, CanFrameFlags, CanIrqSource
from et_test_platform.drivers.dma import DmaIrqEvent, DmaTransferType
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import dependencies
from et_test_platform.test_cases.can import test_can_p2_watchdog as case_module


# 独立响应：载荷按固定向量生成，不从TX请求取回RX Expected。
class WatchdogTarget:
    def __init__(self, fault):
        self.fault = fault
        self.limit = 0
        self.frames = 0
        self.total = 0
        self.stage = 0
        self.initializing = 1
        self.capture = False
        self.cleared = False
        self.commands = []

    # 只接受本Case的固定命令和包长；未知命令失败，不自动返回成功。
    def request(self, service, command, **kwargs):
        assert service == 0x010C and kwargs["body"][0] == 0
        body = kwargs["body"][1:]
        self.commands.append(int(command))
        values = ()
        wdi = int(CanIrqSource.RAM_WATCHDOG)
        triggered = self.frames > 0 and (
            self.limit == 1
            and self.fault != "missing_wdi"
            or self.limit == 0
            and self.fault == "disabled_wdi"
        )
        if command == 1:
            self.initializing = unpack("<I", body)[0]
        elif command == 2:
            values = (self.initializing,)
        elif command == 6:
            options = unpack("<10I", body)
            assert options[:9] == (1, 1, 0, 0, 0, 1, 0, 0, 0)
            self.stage += 1
            assert options[9] == (1 if self.stage == 1 else 0)
            self.limit = options[9]
            self.frames = 0
            self.cleared = False
        elif command == 97:
            values = (self.limit ^ int(self.fault == "config"), 0)
        elif command == 79:
            values = (0x1000 if unpack("<I", body)[0] == 0 else 0x2000,)
        elif command == 39:
            assert body == pack("<2I", wdi, 0)
            self.capture = True
        elif command == 40:
            self.capture = False
        elif command == 38:
            assert body == pack("<I", wdi)
            self.cleared = self.fault != "clear"
        elif command == 37:
            values = (
                wdi if triggered and not self.cleared else 0,
                wdi if self.capture and not triggered else 0,
                0,
                int(self.capture),
            )
        elif command == 41:
            active = wdi if triggered else 0
            values = (
                active,
                active,
                active,
                int(triggered),
                0,
                0,
                self.stage,
                int(self.fault == "irq_fault" and triggered),
            )
            if self.fault == "isr" and triggered:
                values = (active, 0, 0, 1, 0, 0, self.stage, 0)
        elif command == 19:
            values = (0, 1, 0, 2, 0, 0, 0)
        elif command in (84, 85, 20, 83, 82):
            values = self.transfer_response(command, body)
        else:
            sizes = {4: 32, 10: 96, 12: 44, 14: 4, 25: 28, 59: 8, 80: 4}
            assert command in sizes, command
            assert len(body) == sizes[command], (command, len(body))
        return SimpleNamespace(body=pack(f"<{len(values)}I", *values)), None

    # 搬运相关响应与IRQ状态机分开，独立维护固定镜像、FIFO及计数Oracle。
    def transfer_response(self, command, body):
        if command == 84:
            assert len(body) == 84
            values = (72, *([0] * 20))
        elif command == 85:
            assert len(body) == 88
            inverse = self.frames % 2 == 0
            payload = bytes((((0x31 + 17 * i) & 255) ^ (255 if inverse else 0)) for i in range(64))
            if self.fault == "payload":
                payload = bytes(64)
            values = (
                0x123,
                int(CanFrameFlags.FD | CanFrameFlags.BRS),
                15,
                0,
                0,
                0,
                64,
                0xFFFFFFFF,
                *unpack("<16I", payload),
                0,
                0,
                0,
                0,
                0,
            )
        elif command == 20:
            values = (0, 0, 0, 0, 0)
        elif command == 83:
            values = (0, 1, 0)
        elif command == 82:
            values = (self.frames, self.frames - int(self.fault == "counter"), 0, 0, 256)
        else:
            raise AssertionError(f"unexpected transfer command: {command}")
        return values


# DMA替身只允许RX先于TX启动，完成时推进一次固定硬件向量序号。
class DmaStub:
    def __init__(self, target):
        self.target = target
        self.started = []
        self.cleaned = []
        self.configured = set()

    def configure(self, config):
        assert config.channel not in self.configured
        self.configured.add(config.channel)
        assert config.transfer_count == 18
        assert config.transfer_type == (
            DmaTransferType.MEMORY_TO_PERIPHERAL
            if config.channel == 0
            else DmaTransferType.PERIPHERAL_TO_MEMORY
        )

    def start(self, channel):
        assert channel in self.configured
        self.started.append(channel)

    def wait_channels_free(self, channels, *, timeout_s):
        assert channels == (0, 1) and self.started[-2:] == [1, 0] and timeout_s > 0
        self.target.frames += 1
        self.target.total += 1
        return {
            channel: SimpleNamespace(
                is_free=True,
                fifo_empty=True,
                interrupt_events=DmaIrqEvent.ERROR
                if self.target.fault == "dma"
                else DmaIrqEvent(0),
            )
            for channel in channels
        }

    def stop(self, channel):
        self.cleaned.append(channel)

    def deconfigure(self, channel):
        assert channel in (0, 1)
        self.configured.discard(channel)

    def controller_enable(self):
        pass

    def controller_disable(self):
        pass


# 资源地址仅用作软件句柄；不与任何真实板卡连接。
class ResourceStub:
    def __init__(self):
        self.count = 0
        self.resets = 0

    def reset(self):
        self.count = 0
        self.resets += 1

    def create(self, length):
        assert length == 72
        self.count += 1
        return SimpleNamespace(address=0x3000 + 0x100 * self.count)

    def write(self, resource, data):
        assert resource.address in (0x3100, 0x3200) and len(data) == 72

    def read(self, resource):
        assert resource.address == 0x3200
        return bytes(72)


# 计数器使用固定独立样本，停止后仍可读，不从PC时间派生硬件读数。
class TimerStub:
    def __init__(self, fault):
        self.samples = iter((100, 50 if fault == "timer" else 200) * 3)
        self.stopped = False

    def configure(self, config):
        assert (config.period_ticks, config.prescaler_divider) == (0xFFFFFFFF, 256)

    def clear(self):
        pass

    def start(self):
        self.stopped = False

    def stop(self):
        self.stopped = True

    def live_count_get(self):
        return next(self.samples)


# 正常完整流程及每个决定性错误必须产生不同软件结论，所有退出均执行清理。
@pytest.mark.parametrize(
    "fault",
    [
        None,
        "config",
        "missing_wdi",
        "disabled_wdi",
        "isr",
        "irq_fault",
        "clear",
        "payload",
        "dma",
        "counter",
        "timer",
    ],
)
def test_watchdog_case_strict_matrix(fault, monkeypatch):
    support, _, _, calls = dependencies()
    target = WatchdogTarget(fault)
    mapping = support.mapping
    mapping.CAN_DMU_WORD_BYTES = 4
    mapping.CAN_DMU_REQUESTS = {0: {"tx": 3, "rx": 4}}
    support = replace(support, can=CanDriver(target, 0))
    dma, resource, timer = DmaStub(target), ResourceStub(), TimerStub(fault)
    sysctrl = SimpleNamespace(
        configure_dma_request_v2=lambda controller, interface, request: calls.append(
            (controller, interface, request)
        ),
        release_dma_request=lambda controller, interface: calls.append(
            ("release", controller, interface)
        ),
    )
    # PC窗口固定超过100 ms；真实Deadline保持有界，缺少WDI只缩短本软件测试预算。
    ticks = iter(i * 0.2 for i in range(10000))
    monkeypatch.setattr(case_module, "monotonic", lambda: next(ticks))
    if fault == "missing_wdi":
        monkeypatch.setattr(case_module, "TIMEOUT_S", 0.05)
    properties = []
    args = (
        support,
        SimpleNamespace(dma=dma, sysctrl=sysctrl, controller=0),
        (0, timer, SimpleNamespace(maximum_period_ticks=0xFFFFFFFF, maximum_prescaler_divider=256)),
        resource,
        lambda k, v: properties.append((k, v)),
    )
    if fault:
        with pytest.raises(RequestTimeout if fault == "missing_wdi" else AssertionError):
            case_module.test_can_p2_010_ram_watchdog(*args)
    else:
        case_module.test_can_p2_010_ram_watchdog(*args)
        assert target.total == 17 and target.stage == 3
        assert target.commands.count(38) == 3
        assert dict(properties)["recovery"]["stage"] == "recovery"
    assert dma.cleaned == [0, 1] and timer.stopped and resource.count == 0
    assert calls[-1] == ("can", 0)
