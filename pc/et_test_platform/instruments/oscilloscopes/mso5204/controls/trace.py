# RIGOL MSO5204 AWG Arbitrary Trace 原子控制。
#
# 职责：映射 TRACe<n>:DATA:DAC16，将 14-bit 任意波形点下载到指定 AWG 易失存储器。
# 边界：不缩放用户数据、不自动打开 AWG 输出，也不拆分为多次传输。
# 依赖：仅依赖公共 ScpiSession 的 IEEE488.2 definite-length block 写入。

from __future__ import annotations

from ....common.scpi import ScpiSession


# 提供 AWG 任意波形块下载接口；构造时仅保存 Session，不访问或改变仪器状态。
class Mso5204TraceControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 下载指定 AWG 通道的 DAC16 任意波形二进制数据，只执行一次 definite block 写入。
    def dac16_data_set(self, source: int, payload: bytes) -> None:
        channel = int(source)
        if channel not in {1, 2}:
            raise ValueError("AWG source must be 1 or 2")
        data = bytes(payload)
        if not 4 <= len(data) <= 32768 or len(data) % 2:
            raise ValueError("DAC16 payload must contain 4..32768 bytes and have even length")
        self._session.write_definite_block(
            f":TRACe{channel}:DATA:DAC16 volatile,END,",
            data,
            separator="",
        )
