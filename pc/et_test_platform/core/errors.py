# 平台异常 的跨 IP 公共基础实现。
#
# 职责：提供芯片无关的平台异常语义，供 Driver、Case 和通信层复用。
# 边界：不包含任何 IP Command、Wire 字段、Bench 事实或设备 I/O。
# 依赖：仅依赖 Python 标准库和 core 层内部稳定类型。


# 提供 EtPlatformError 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class EtPlatformError(Exception):
    pass


# 提供 ProtocolError 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class ProtocolError(EtPlatformError):
    pass


# 提供 TransportError 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class TransportError(EtPlatformError):
    pass


# 提供 RequestTimeout 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class RequestTimeout(TransportError):
    pass


# 提供 OperationBusy 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class OperationBusy(EtPlatformError):
    pass


# 提供 TargetRejected 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class TargetRejected(EtPlatformError):
    def __init__(
        self,
        *,
        service_id: int,
        command_id: int,
        instance_id: int,
        status: int,
        body: bytes = b"",
        status_name: str = "",
    ) -> None:
        self.service_id = service_id
        self.command_id = command_id
        self.instance_id = instance_id
        self.status = status
        self.body = bytes(body)
        label = status_name or str(status)
        super().__init__(
            "target rejected "
            f"service=0x{service_id:04x} "
            f"command=0x{command_id:04x} "
            f"instance={instance_id} status={label}"
        )


# 提供 ConfigurationError 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class ConfigurationError(EtPlatformError):
    pass


# 提供 CapabilityLookupError 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class CapabilityLookupError(EtPlatformError):
    pass


# 提供 UnsupportedCapability 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class UnsupportedCapability(CapabilityLookupError):
    pass
