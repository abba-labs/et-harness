# B&K Precision 9130B 通道选择、组合和触发耦合控制。
#
# 职责：映射 INSTrument 通道选择、串并联/跟踪组合以及触发耦合等原子命令。
# 边界：不修改物理接线、不打开输出，也不把多个组合模式切换隐藏在一个 API 中。
# 依赖：仅依赖 ScpiSession、本型号 Models 和 Validation。

from __future__ import annotations

from collections.abc import Iterable

from ....common.scpi import ScpiSession
from ..models import Bk9130bChannel
from ..validation import format_channels, require_integer


# 提供 9130B 通道级单命令控制；组合接线正确性和冲突由调用方与仪器共同保证。
class Bk9130bChannelControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 按 CH1/CH2/CH3 名称选择当前通道；只修改当前通道上下文。
    def select_set(self, channel: Bk9130bChannel) -> None:
        if not isinstance(channel, Bk9130bChannel):
            raise ValueError("channel must be Bk9130bChannel")
        self._session.write(f"INSTrument:SELect {channel.value}")

    # 查询当前通道名称；查询过程不会改变当前通道选择。
    def select_get(self) -> Bk9130bChannel:
        response = self._session.query_text("INSTrument:SELect?").strip().upper()
        try:
            return Bk9130bChannel(response)
        except ValueError as exc:
            raise ValueError(f"unexpected channel response: {response!r}") from exc

    # 按 1~3 数字选择当前通道；只修改当前通道上下文。
    def number_set(self, channel: int) -> None:
        self._session.write(f"INSTrument:NSELect {require_integer(channel, 1, 3, 'channel')}")

    # 查询当前数字通道选择；查询过程不会改变当前通道。
    def number_get(self) -> int:
        return int(self._session.query_text("INSTrument:NSELect?"))

    # 把指定通道设置为串联组合；禁用时按手册传 NONE，不执行额外模式切换。
    def combine_series_set(self, channels: Iterable[Bk9130bChannel] | None) -> None:
        value = "NONE" if channels is None else format_channels(channels)
        self._session.write(f"INSTrument:COMbine:SERies {value}")

    # 把指定通道设置为并联组合；禁用时按手册传 NONE，不执行额外模式切换。
    def combine_parallel_set(self, channels: Iterable[Bk9130bChannel] | None) -> None:
        value = "NONE" if channels is None else format_channels(channels)
        self._session.write(f"INSTrument:COMbine:PARAllel {value}")

    # 把指定通道设置为跟踪组合；禁用时按手册传 NONE，不执行额外模式切换。
    def combine_tracking_set(self, channels: Iterable[Bk9130bChannel] | None) -> None:
        value = "NONE" if channels is None else format_channels(channels)
        self._session.write(f"INSTrument:COMbine:TRAck {value}")

    # 设置 *TRG 影响的通道列表；只修改触发耦合配置，不产生触发。
    def couple_trigger_set(self, channels: Iterable[Bk9130bChannel]) -> None:
        self._session.write(f"INSTrument:COUPle:TRIGger {format_channels(channels)}")

    # 查询 *TRG 当前耦合通道列表；查询过程不会产生触发。
    def couple_trigger_get(self) -> tuple[Bk9130bChannel, ...]:
        response = self._session.query_text("INSTrument:COUPle:TRIGger?")
        try:
            return tuple(Bk9130bChannel(item.strip().upper()) for item in response.split(","))
        except ValueError as exc:
            raise ValueError(f"unexpected trigger coupling response: {response!r}") from exc
