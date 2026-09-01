# 示波器逻辑信号观测公共接口。
#
# 职责：为 Formal Case 提供芯片和仪器型号中立的边沿捕获、运行控制与测量语义。
# 边界：不选择物理通道、不解析 Bench、不决定 PASS/FAIL，也不实现具体 SCPI 命令。
# 依赖：仅依赖 Python 标准库的 Protocol、dataclass 与 Enum。

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


# 表示逻辑信号边沿方向；具体仪器 Adapter 负责转换为厂商命令词汇。
class SignalEdge(str, Enum):
    RISING = "rising"
    FALLING = "falling"
    EITHER = "either"


# 表示一次示波器自动测量快照；全部字段使用 SI 单位且不包含测试阈值。
@dataclass(frozen=True, slots=True)
class SignalObservation:
    frequency_hz: float
    period_s: float
    positive_width_s: float
    duty_cycle_percent: float
    vpp_v: float


# 定义 Formal Case 可依赖的最小示波器行为；实现必须保留真实设备错误和超时。
@runtime_checkable
class SignalObserver(Protocol):
    # 返回稳定设备连接身份，供 Evidence 标记真实观测来源；读取属性不得触发设备 I/O。
    @property
    def identity(self) -> str: ...

    # 打开已显式配置的仪器连接；不得扫描或选择其他设备。
    def open(self) -> None: ...

    # 关闭当前仪器连接并释放通信资源；不得隐式改变 DUT 状态或清除测试证据。
    def close(self) -> None: ...

    # 按 Case 时基和边沿配置捕获；模拟前端事实由 Bench 绑定提供。
    def configure_edge_capture(self, *, time_scale_s: float, edge: SignalEdge) -> None: ...

    # Arm 一次单次采集并保持已配置触发条件；不强制产生触发，也不等待采集完成。
    def arm_single(self) -> None: ...

    # 启动连续采集并保持当前模拟前端配置；不读取测量值，也不形成测试结论。
    def run(self) -> None: ...

    # 停止当前采集以稳定后续测量读取；不得丢弃已捕获波形或修改 DUT 输出。
    def stop(self) -> None: ...

    # 读取一次统一物理量快照；不应用 Case 容差或 PASS/FAIL 阈值。
    def measure(self) -> SignalObservation: ...


__all__ = ["SignalEdge", "SignalObservation", "SignalObserver"]
