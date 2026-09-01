# FRAMEWORK PC Driver Package 的driver层。
#
# 职责：提供 FRAMEWORK 的单 IP 稳定业务 API、Deadline/Retry/Polling 与单 IP Cleanup。
# 边界：不调用其他 IP Driver、不读取原始 Bench/Profile、不执行 pytest 结论。
# 依赖：仅依赖本 IP Model/Contract/Codec/Validation 与 TargetClient。

from __future__ import annotations

import secrets
import time
from collections.abc import Callable

from ...clients.target import TargetClient
from ...core.errors import ProtocolError
from .codec import (
    decode_hello,
    decode_reset_reason,
    decode_service_list,
    decode_statistics,
    decode_version,
    registry_hash,
)
from .contract import (
    FRAMEWORK_INSTANCE_ID,
    FRAMEWORK_SERVICE_ID,
    FrameworkCommand,
)
from .models import (
    EchoExchange,
    HelloInfo,
    ProtocolStatistics,
    ServiceInfo,
    VersionInfo,
)
from .validation import require_session_id


# Firmware Framework Service 的稳定 PC 客户端；负责会话握手、服务发现和公共只读查询，不解释具体 IP 业务。
class FrameworkDriver:
    def __init__(
        self,
        target: TargetClient,
        *,
        clock: Callable[[], float] = time.monotonic,
        session_id_factory: Callable[[], int] | None = None,
    ) -> None:
        self._target = target
        self._clock = clock
        self._session_id_factory = (
            _new_session_id if session_id_factory is None else session_id_factory
        )
        self._hello: HelloInfo | None = None
        self._runtime_services: tuple[ServiceInfo, ...] | None = None

    # 返回当前 TargetClient 的通信身份；只读取本地属性，不发送 Framework 请求。
    @property
    def transport_identity(self) -> str:

        return self._target.identity

    # 返回当前会话使用的 TargetClient，供 IP-local Fixture/Support 构造单 IP Driver；不发送请求。
    @property
    def target_client(self) -> TargetClient:

        return self._target

    # 返回最近一次成功 HELLO 缓存的芯片 ID；未完成 HELLO 时明确失败，不发送请求。
    @property
    def chip_id(self) -> str:

        return self._require_hello().chip_id

    # 返回最近一次成功 HELLO 缓存的 Firmware Build ID；未完成 HELLO 时明确失败，不发送请求。
    @property
    def firmware_build_id(self) -> str:

        return self._require_hello().firmware_build_id

    # 返回最近一次成功 HELLO 缓存的 Firmware Service Registry 指纹；不发送请求。
    @property
    def registry_hash(self) -> str:

        return self._require_hello().registry_hash

    # 返回最近一次完整校验通过的 Firmware Service Registry；未发现或发现失败时拒绝读取旧缓存。
    @property
    def runtime_services(self) -> tuple[ServiceInfo, ...]:

        if self._runtime_services is None:
            raise RuntimeError("FrameworkDriver.discover_services() must run first")
        return self._runtime_services

    # 发送一次 HELLO，校验协议版本和 Session 后缓存身份事实；失败时不发布 HELLO 或 Service Registry 缓存。
    def hello(self) -> HelloInfo:

        self._hello = None
        self._runtime_services = None
        proposed_session_id = require_session_id(self._session_id_factory())
        message, frame = self._target.request(
            FRAMEWORK_SERVICE_ID,
            FrameworkCommand.HELLO,
            instance_id=FRAMEWORK_INSTANCE_ID,
            session_id=proposed_session_id,
            retry_safe=True,
        )
        if frame.session_id != proposed_session_id:
            raise ProtocolError("HELLO response did not accept the proposed session")
        info = decode_hello(message.body)
        if info.protocol_version != 1:
            raise ProtocolError(
                f"target reports unsupported protocol version {info.protocol_version}"
            )
        self._target.bind_session(frame.session_id)
        self._hello = info
        return info

    # 发送一次 ECHO 并返回响应、延迟和重试增量；只等待本次 Target 请求，不解释 Payload 的业务含义。
    def echo(self, payload: bytes) -> EchoExchange:

        retry_before = self._target.retry_count
        started = self._clock()
        message, _ = self._target.request(
            FRAMEWORK_SERVICE_ID,
            FrameworkCommand.ECHO,
            instance_id=FRAMEWORK_INSTANCE_ID,
            body=payload,
            retry_safe=True,
        )
        return EchoExchange(
            response=message.body,
            latency_ms=(self._clock() - started) * 1000.0,
            retry_count=self._target.retry_count - retry_before,
        )

    # 查询 Firmware VERSION_GET 并返回解码后的版本事实；只等待本次 Target 响应。
    def version_get(self) -> VersionInfo:

        message, _ = self._target.request(
            FRAMEWORK_SERVICE_ID,
            FrameworkCommand.VERSION_GET,
            instance_id=FRAMEWORK_INSTANCE_ID,
            retry_safe=True,
        )
        return decode_version(message.body)

    # 查询 Firmware SERVICE_LIST 并返回当前注册 Service 事实；只等待本次 Target 响应，不修改发现缓存。
    def service_list(self) -> tuple[ServiceInfo, ...]:

        message, _ = self._target.request(
            FRAMEWORK_SERVICE_ID,
            FrameworkCommand.SERVICE_LIST,
            instance_id=FRAMEWORK_INSTANCE_ID,
            retry_safe=True,
        )
        return decode_service_list(message.body)

    # 读取 SERVICE_LIST 并与 HELLO Registry 指纹核对；仅在完整校验成功后发布新缓存，失败保持未发现状态。
    def discover_services(self) -> tuple[ServiceInfo, ...]:

        self._runtime_services = None
        hello = self._require_hello()
        services = self.service_list()
        if len(set(services)) != len(services):
            raise ProtocolError("SERVICE_LIST contains duplicate entries")
        actual_hash = registry_hash(services)
        if actual_hash != hello.registry_hash:
            raise ProtocolError(
                "firmware registry hash mismatch: "
                f"HELLO={hello.registry_hash!r}, SERVICE_LIST={actual_hash!r}"
            )
        self._runtime_services = services
        return services

    # 查询 Framework 协议统计并返回当前计数事实；只等待本次 Target 响应，不改变协议状态。
    def statistics_get(self) -> ProtocolStatistics:

        message, _ = self._target.request(
            FRAMEWORK_SERVICE_ID,
            FrameworkCommand.STATISTICS_GET,
            instance_id=FRAMEWORK_INSTANCE_ID,
            retry_safe=True,
        )
        return decode_statistics(message.body)

    # 查询 Firmware Reset Reason 并返回原始原因值；只等待本次 Target 响应，不形成测试结论。
    def reset_reason_get(self) -> int:

        message, _ = self._target.request(
            FRAMEWORK_SERVICE_ID,
            FrameworkCommand.RESET_REASON_GET,
            instance_id=FRAMEWORK_INSTANCE_ID,
            retry_safe=True,
        )
        return decode_reset_reason(message.body)

    # 返回已缓存的 HELLO 身份；调用方尚未完成 HELLO 时明确失败，避免使用未建立会话的旧事实。
    def _require_hello(self) -> HelloInfo:
        if self._hello is None:
            raise RuntimeError("FrameworkDriver.hello() must run first")
        return self._hello


# 生成非零 32-bit Session ID；仅产生本地随机值，不访问 Target 或修改通信状态。
def _new_session_id() -> int:
    value = 0
    while value == 0:
        value = secrets.randbits(32)
    return value
