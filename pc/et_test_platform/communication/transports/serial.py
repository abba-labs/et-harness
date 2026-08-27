# 串口 ByteTransport 的具体实现。
#
# 职责：把一次 PC 字节读写映射到 pyserial，并在调用范围内应用读写超时。
# 边界：不解析协议帧、不解释 IP Command，也不做重试或跨请求 Deadline 分配。
# 依赖：仅依赖 ByteTransport 接口、pyserial 和平台 TransportError。

from __future__ import annotations

from contextlib import suppress
from typing import Any

from ...core.deadline import require_positive_seconds
from ...core.errors import TransportError
from ..transport import ByteTransport

_READ_POLL_TIMEOUT_S = 0.02
_WRITE_TIMEOUT_S = 1.0


# 提供 SerialTransport 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class SerialTransport(ByteTransport):
    def __init__(
        self,
        *,
        port: str,
        baudrate: int,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        dtr: bool = False,
        rts: bool = False,
    ) -> None:
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._dtr = dtr
        self._rts = rts
        self._serial: Any | None = None

    # 提供 identity 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    @property
    def identity(self) -> str:

        return f"serial:{self._port}@{self._baudrate}"

    # 提供 open 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    def open(self) -> None:

        try:
            import serial
        except ImportError as exc:
            raise TransportError("pyserial is required for serial targets") from exc

        serial_port: Any | None = None
        try:
            # pyserial 以 port=None 创建未打开对象；先设置控制线再显式打开，
            # 避免部分 USB 转串口在构造时自动打开并产生 DTR/RTS 毛刺。
            serial_port = serial.Serial(
                port=None,
                baudrate=self._baudrate,
                bytesize=self._bytesize,
                parity=self._parity,
                stopbits=self._stopbits,
                timeout=_READ_POLL_TIMEOUT_S,
                write_timeout=_WRITE_TIMEOUT_S,
            )
            serial_port.port = self._port
            serial_port.dtr = self._dtr
            serial_port.rts = self._rts
            serial_port.open()
            self._serial = serial_port
        except Exception as exc:
            if serial_port is not None:
                with suppress(Exception):
                    serial_port.close()
            self._serial = None
            raise TransportError(f"cannot open {self.identity}: {exc}") from exc

    # 提供 close 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    def close(self) -> None:

        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None

    # 提供 write 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    def write(
        self,
        data: bytes,
        *,
        timeout_s: float | None = None,
    ) -> None:

        if self._serial is None:
            raise TransportError("serial transport is not open")
        timeout = (
            _WRITE_TIMEOUT_S
            if timeout_s is None
            else require_positive_seconds(timeout_s, "timeout_s")
        )
        previous_timeout = self._serial.write_timeout
        try:
            self._serial.write_timeout = timeout
            written = self._serial.write(data)
        except Exception as exc:
            raise TransportError(f"serial write failed: {exc}") from exc
        finally:
            self._serial.write_timeout = previous_timeout
        if written != len(data):
            raise TransportError(f"short serial write: expected {len(data)}, wrote {written}")

    # 提供 read 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    def read(
        self,
        max_bytes: int,
        timeout_s: float | None = None,
    ) -> bytes:

        if self._serial is None:
            raise TransportError("serial transport is not open")
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        timeout = (
            _READ_POLL_TIMEOUT_S
            if timeout_s is None
            else require_positive_seconds(timeout_s, "timeout_s")
        )
        previous_timeout = self._serial.timeout
        try:
            self._serial.timeout = timeout
            first = bytes(self._serial.read(1))
            if not first:
                return b""
            available = min(max_bytes - 1, int(self._serial.in_waiting))
            return first + (bytes(self._serial.read(available)) if available > 0 else b"")
        except Exception as exc:
            raise TransportError(f"serial read failed: {exc}") from exc
        finally:
            self._serial.timeout = previous_timeout
