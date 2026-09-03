# CRG PC Driver Package 的driver层。
#
# 职责：提供 CRG 的单 IP 稳定业务 API、Deadline/Retry/Polling 与单 IP Cleanup。
# 边界：不调用其他 IP Driver、不读取原始 Bench/Profile、不执行 pytest 结论。
# 依赖：仅依赖本 IP Model/Contract/Codec/Validation 与 TargetClient。

from __future__ import annotations

from ...clients.target import TargetClient
from .codec import (
    decode_syscnt_clock,
    decode_wdg_clock,
    encode_clock_set,
    encode_reset,
    encode_syscnt_clock,
    encode_wdg_clock_get,
    encode_wdg_clock_set,
)
from .contract import CRG_SERVICE_ID, CrgCommand
from .models import CrgPeripheral, CrgWdgClockConfig, CrgWdgClockSource
from .validation import enabled_value, instance_value, peripheral_value


# CRG Service 的稳定单 IP 客户端。
class CrgDriver:
    def __init__(self, target: TargetClient) -> None:
        self._target = target

    # 发送 clock set 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def clock_set(
        self,
        peripheral: CrgPeripheral,
        *,
        instance: int,
        enabled: bool,
    ) -> None:

        self._target.request(
            CRG_SERVICE_ID,
            CrgCommand.CLOCK_SET,
            body=encode_clock_set(
                peripheral_value(peripheral),
                instance_value(instance),
                enabled_value(enabled),
            ),
        )

    # 发送 reset 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def reset(self, peripheral: CrgPeripheral, *, instance: int) -> None:

        self._target.request(
            CRG_SERVICE_ID,
            CrgCommand.RESET,
            body=encode_reset(
                peripheral_value(peripheral),
                instance_value(instance),
            ),
        )

    # 选择逻辑 WDG 的片内时钟源和编码分频；只等待本次响应，失败或超时按平台异常上抛。
    def wdg_clock_set(
        self,
        wdg_id: int,
        *,
        source: CrgWdgClockSource,
        divider: int = 0,
    ) -> None:

        if isinstance(wdg_id, bool) or not isinstance(wdg_id, int) or not 0 <= wdg_id <= 0xFF:
            raise ValueError("wdg_id must be an unsigned 8-bit integer")
        if isinstance(divider, bool) or not isinstance(divider, int) or not 0 <= divider <= 0xFF:
            raise ValueError("divider must be an unsigned 8-bit integer")

        self._target.request(
            CRG_SERVICE_ID,
            CrgCommand.WDG_CLOCK_SET,
            body=encode_wdg_clock_set(wdg_id, int(source), divider),
        )

    # 读取逻辑 WDG 的时钟源和编码分频事实；只等待本次响应，失败或超时按平台异常上抛。
    def wdg_clock_get(self, wdg_id: int) -> CrgWdgClockConfig:

        if isinstance(wdg_id, bool) or not isinstance(wdg_id, int) or not 0 <= wdg_id <= 0xFF:
            raise ValueError("wdg_id must be an unsigned 8-bit integer")

        message, _ = self._target.request(
            CRG_SERVICE_ID,
            CrgCommand.WDG_CLOCK_GET,
            body=encode_wdg_clock_get(wdg_id),
            retry_safe=True,
        )
        source, divider = decode_wdg_clock(message.body)

        try:
            normalized_source = CrgWdgClockSource(source)
        except ValueError as error:
            raise ValueError(f"unsupported CRG WDG clock source: {source}") from error

        return CrgWdgClockConfig(source=normalized_source, divider=divider)

    # 只设置系统计数器时钟门控，不复位计数器，也不改变时钟源。
    # 仅等待单次命令响应，不轮询；通信超时或固件拒绝按平台异常上抛，非法响应体抛ValueError。
    def syscnt_clock_set(self, instance: int, *, enabled: bool) -> None:

        message, _ = self._target.request(
            CRG_SERVICE_ID,
            CrgCommand.SYSCNT_CLOCK_SET,
            body=encode_syscnt_clock(instance_value(instance), enabled_value(enabled)),
        )
        if message.body:
            raise ValueError("CRG SYSCNT clock SET returned an unexpected body")

    # 读取实际门控状态；不得用该Boolean或请求值推导计数频率。
    # 仅等待单次只读请求，不等待状态变化；通信超时、固件拒绝或无效响应直接上抛。
    def syscnt_clock_get(self, instance: int) -> bool:

        message, _ = self._target.request(
            CRG_SERVICE_ID,
            CrgCommand.SYSCNT_CLOCK_GET,
            body=encode_syscnt_clock(instance_value(instance)),
            retry_safe=True,
        )

        return decode_syscnt_clock(message.body)
