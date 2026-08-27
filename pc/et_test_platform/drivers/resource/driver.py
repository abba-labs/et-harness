# RESOURCE PC Driver Package 的driver层。
#
# 职责：提供 RESOURCE 的单 IP 稳定业务 API、Deadline/Retry/Polling 与单 IP Cleanup。
# 边界：不调用其他 IP Driver、不读取原始 Bench/Profile、不执行 pytest 结论。
# 依赖：仅依赖本 IP Model/Contract/Codec/Validation、Core Cleanup 与 TargetClient。

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from ...clients.target import TargetClient
from ...communication.protocols.et_frame import Frame
from ...communication.protocols.et_message import ServiceMessage
from ...core.cleanup import OperationCleanupError, raise_with_cleanup, run_cleanup
from .codec import (
    decode_created,
    decode_info,
    encode_create,
    encode_fill,
    encode_info,
    encode_read,
    encode_write,
    validate_read_body,
)
from .contract import (
    RESOURCE_INSTANCE_ID,
    RESOURCE_SERVICE_ID,
    RESOURCE_TRANSFER_CHUNK,
    ResourceCommand,
)
from .models import ResourceRef
from .validation import (
    require_uint32,
    validate_fill_value,
    validate_range,
)


# Firmware 固定池 Resource Service 的稳定单 IP 客户端。
class ResourceDriver:
    def __init__(self, target: TargetClient) -> None:
        self._target = target

    # 发送 reset 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def reset(self) -> None:

        self._request(ResourceCommand.RESET)

    # 进入时重置固定 Resource Pool，退出时再次重置；不等待后续硬件完成，主错误与 Cleanup 错误同时保留。
    @contextmanager
    def pool_mode(self) -> Iterator[None]:

        with self._cleanup_mode(
            "Resource pool mode",
            (("Resource pool reset", self.reset),),
        ):
            self.reset()
            yield

    # 发送 create 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def create(self, size: int, alignment: int = 4) -> ResourceRef:

        size_value = require_uint32(size, "size", nonzero=True)
        alignment_value = require_uint32(alignment, "alignment", nonzero=True)
        if alignment_value & (alignment_value - 1):
            raise ValueError("Resource alignment must be a power of two")
        message, _ = self._request(
            ResourceCommand.CREATE,
            encode_create(size_value, alignment_value),
        )
        return decode_created(message.body)

    # 执行 write 操作并在调用方总 Deadline 内等待所需完成事实；Target 拒绝、协议错误或超时以平台异常上抛，Cleanup 失败保留独立错误上下文。
    def write(self, resource: ResourceRef, data: bytes, offset: int = 0) -> None:

        payload = bytes(data)
        offset_value, _ = validate_range(
            resource,
            offset=offset,
            size=len(payload),
            operation="write",
        )
        for chunk_offset in range(0, len(payload), RESOURCE_TRANSFER_CHUNK):
            chunk = payload[chunk_offset : chunk_offset + RESOURCE_TRANSFER_CHUNK]
            self._request(
                ResourceCommand.WRITE,
                encode_write(
                    resource.handle,
                    offset_value + chunk_offset,
                    chunk,
                ),
            )

    # 发送 read 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def read(
        self,
        resource: ResourceRef,
        size: int | None = None,
        offset: int = 0,
    ) -> bytes:

        requested = resource.size - offset if size is None else size
        offset_value, size_value = validate_range(
            resource,
            offset=offset,
            size=requested,
            operation="read",
        )
        result = bytearray()
        for chunk_offset in range(0, size_value, RESOURCE_TRANSFER_CHUNK):
            chunk_size = min(
                RESOURCE_TRANSFER_CHUNK,
                size_value - chunk_offset,
            )
            message, _ = self._request(
                ResourceCommand.READ,
                encode_read(
                    resource.handle,
                    offset_value + chunk_offset,
                    chunk_size,
                ),
            )
            result.extend(validate_read_body(message.body, chunk_size))
        return bytes(result)

    # 发送 fill 对应的当前 IP 操作；不等待后续硬件完成，Target 拒绝、协议错误或超时按平台异常上抛，跨 IP 顺序由 Test Case 负责。
    def fill(
        self,
        resource: ResourceRef,
        value: int,
        size: int | None = None,
        offset: int = 0,
    ) -> None:

        requested = resource.size - offset if size is None else size
        offset_value, size_value = validate_range(
            resource,
            offset=offset,
            size=requested,
            operation="fill",
        )
        self._request(
            ResourceCommand.FILL,
            encode_fill(
                resource.handle,
                offset_value,
                size_value,
                validate_fill_value(value),
            ),
        )

    # 读取 info 对应的当前 IP 事实；只等待本次 Target 响应，不等待后续硬件动作，Target 拒绝、协议错误或超时按平台异常上抛。
    def info(self, handle: int) -> ResourceRef:

        handle_value = require_uint32(handle, "handle", nonzero=True)
        message, _ = self._request(
            ResourceCommand.INFO_GET,
            encode_info(handle_value),
        )
        return decode_info(handle_value, message.body)

    # Preserve the primary failure while completing one-IP cleanup.
    @contextmanager
    def _cleanup_mode(
        self,
        label: str,
        actions: tuple[tuple[str, Callable[[], object]], ...],
    ) -> Iterator[None]:

        try:
            yield
        except BaseException as primary_error:
            cleanup_failures = run_cleanup(actions)
            if isinstance(primary_error, OperationCleanupError) and cleanup_failures:
                raise OperationCleanupError(
                    primary_error.primary_error,
                    (*primary_error.cleanup_failures, *cleanup_failures),
                ) from primary_error
            raise_with_cleanup(primary_error, cleanup_failures)
        cleanup_failures = run_cleanup(actions)
        if cleanup_failures:
            raise_with_cleanup(
                RuntimeError(f"{label} completed but cleanup did not"),
                cleanup_failures,
            )

    def _request(
        self,
        command: ResourceCommand,
        body: bytes = b"",
    ) -> tuple[ServiceMessage, Frame]:
        return self._target.request(
            RESOURCE_SERVICE_ID,
            command,
            instance_id=RESOURCE_INSTANCE_ID,
            body=body,
        )
