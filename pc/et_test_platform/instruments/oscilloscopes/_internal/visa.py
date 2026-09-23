# 示波器库自包含 VISA 字节 Transport。
#
# 职责：把一次原始字节读写映射到 PyVISA MessageBasedResource，并管理资源生命周期。
# 边界：不扫描仪器、不解释 SCPI 语义，也不选择具体 VISA backend 或物理接口。
# 依赖：仅依赖本库 ByteTransport、Deadline 校验和传输异常。

from __future__ import annotations

from contextlib import suppress
from typing import Any

from .deadline import require_positive_seconds
from .errors import TransportError
from .transport import ByteTransport

_DEFAULT_OPEN_TIMEOUT_S = 5.0
_DEFAULT_IO_TIMEOUT_S = 2.0


# 提供 USBTMC、TCPIP/VXI-11 和 GPIB 共用的原始字节 Transport。
class VisaTransport(ByteTransport):
    def __init__(
        self,
        *,
        resource_name: str,
        visa_library: str | None = None,
        open_timeout_s: float = _DEFAULT_OPEN_TIMEOUT_S,
    ) -> None:
        normalized = resource_name.strip()
        if not normalized:
            raise ValueError("resource_name must not be empty")
        if "\r" in normalized or "\n" in normalized:
            raise ValueError("resource_name must contain exactly one VISA resource")
        self._resource_name = normalized
        self._visa_library = visa_library
        self._open_timeout_s = require_positive_seconds(open_timeout_s, "open_timeout_s")
        self._resource_manager: Any | None = None
        self._resource: Any | None = None
        self._timeout_error_code: Any | None = None
        self._rx_buffer = bytearray()

    # 返回稳定 VISA 资源标识；构造和读取该属性都不会访问真实仪器。
    @property
    def identity(self) -> str:
        return f"visa:{self._resource_name}"

    # 打开显式指定的 VISA 资源；不扫描设备，也不发送任何仪器命令。
    def open(self) -> None:
        if self._resource is not None:
            raise TransportError(f"{self.identity} is already open")

        try:
            import pyvisa
        except ImportError as exc:
            raise TransportError(
                "PyVISA is required for VISA instruments; install the project dependencies"
            ) from exc

        manager: Any | None = None
        resource: Any | None = None
        try:
            manager = (
                pyvisa.ResourceManager(self._visa_library)
                if self._visa_library is not None
                else pyvisa.ResourceManager()
            )
            resource = manager.open_resource(
                self._resource_name,
                open_timeout=_seconds_to_milliseconds(self._open_timeout_s),
            )
        except Exception as exc:
            if resource is not None:
                with suppress(Exception):
                    resource.close()
            if manager is not None:
                with suppress(Exception):
                    manager.close()
            raise TransportError(f"cannot open {self.identity}: {exc}") from exc

        self._resource_manager = manager
        self._resource = resource
        self._timeout_error_code = _find_timeout_error_code(pyvisa)
        self._rx_buffer.clear()

    # 关闭仪器资源和 ResourceManager；即使仪器关闭失败也继续释放 Manager。
    def close(self) -> None:
        resource = self._resource
        manager = self._resource_manager
        self._resource = None
        self._resource_manager = None
        self._timeout_error_code = None
        self._rx_buffer.clear()

        errors: list[str] = []
        if resource is not None:
            try:
                resource.close()
            except Exception as exc:
                errors.append(f"resource close failed: {exc}")
        if manager is not None:
            try:
                manager.close()
            except Exception as exc:
                errors.append(f"resource manager close failed: {exc}")
        if errors:
            raise TransportError(f"cannot close {self.identity}: {'; '.join(errors)}")

    # 写入完整原始字节；临时应用本次调用的 I/O Timeout，并拒绝短写。
    def write(
        self,
        data: bytes,
        *,
        timeout_s: float | None = None,
    ) -> None:
        resource = self._require_open_resource()
        timeout = (
            _DEFAULT_IO_TIMEOUT_S
            if timeout_s is None
            else require_positive_seconds(timeout_s, "timeout_s")
        )
        previous_timeout = resource.timeout
        try:
            resource.timeout = _seconds_to_milliseconds(timeout)
            written = resource.write_raw(bytes(data))
        except Exception as exc:
            raise TransportError(f"VISA write failed for {self.identity}: {exc}") from exc
        finally:
            resource.timeout = previous_timeout
        if written != len(data):
            raise TransportError(f"short VISA write: expected {len(data)}, wrote {written}")

    # 读取不超过 max_bytes 的原始字节；完整 VISA 消息过长时由本 Transport 暂存余量。
    def read(
        self,
        max_bytes: int,
        timeout_s: float | None = None,
    ) -> bytes:
        resource = self._require_open_resource()
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if self._rx_buffer:
            return self._take_buffered(max_bytes)

        timeout = (
            _DEFAULT_IO_TIMEOUT_S
            if timeout_s is None
            else require_positive_seconds(timeout_s, "timeout_s")
        )
        previous_timeout = resource.timeout
        try:
            resource.timeout = _seconds_to_milliseconds(timeout)
            self._rx_buffer.extend(bytes(resource.read_raw()))
        except Exception as exc:
            if self._is_timeout(exc):
                return b""
            raise TransportError(f"VISA read failed for {self.identity}: {exc}") from exc
        finally:
            resource.timeout = previous_timeout
        return self._take_buffered(max_bytes)

    def _require_open_resource(self) -> Any:
        if self._resource is None:
            raise TransportError("VISA transport is not open")
        return self._resource

    def _take_buffered(self, max_bytes: int) -> bytes:
        result = bytes(self._rx_buffer[:max_bytes])
        del self._rx_buffer[:max_bytes]
        return result

    def _is_timeout(self, exc: Exception) -> bool:
        return self._timeout_error_code is not None and (
            getattr(exc, "error_code", None) == self._timeout_error_code
        )


def _seconds_to_milliseconds(seconds: float) -> int:
    return max(1, int(seconds * 1000))


def _find_timeout_error_code(pyvisa_module: Any) -> Any | None:
    constants = getattr(pyvisa_module, "constants", None)
    status_code = getattr(constants, "StatusCode", None)
    return getattr(status_code, "error_timeout", None)
