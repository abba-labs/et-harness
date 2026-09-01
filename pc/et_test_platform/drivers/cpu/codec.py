# CPU Owner Wire 编解码。
# 职责：严格转换固定长度的 Request/Response。
# 边界：不执行 I/O、轮询、Capability 查询或测试判断。
# 依赖：仅依赖 CPU Contract、Model 和公共协议异常。

from ...core.errors import ProtocolError
from .contract import (
    CAPABILITIES_STRUCT,
    CONFIG_STRUCT,
    CPU_SERVICE_API_VERSION,
    SNAPSHOT_STRUCT,
)
from .models import CpuNmiCapabilities, CpuNmiSnapshot


# 编码固定四字节NMI配置请求；只做类型/范围校验和纯字节转换。
def encode_nmi_configure(nmi_mask: int) -> bytes:
    if isinstance(nmi_mask, bool) or not isinstance(nmi_mask, int) or not 0 <= nmi_mask <= 0xFF:
        raise ValueError("nmi_mask must be an unsigned 8-bit integer")
    return CONFIG_STRUCT.pack(nmi_mask)


# 解码CPU Owner能力响应；拒绝版本、长度和源掩码不符合契约的响应。
def decode_capabilities(body: bytes) -> CpuNmiCapabilities:
    if len(body) != CAPABILITIES_STRUCT.size:
        raise ProtocolError("CPU CAPABILITIES_GET response length is invalid")
    api_version, struct_size, source_mask = CAPABILITIES_STRUCT.unpack(body)
    if api_version != CPU_SERVICE_API_VERSION or struct_size != CAPABILITIES_STRUCT.size:
        raise ProtocolError("CPU CAPABILITIES_GET version or size is incompatible")
    if source_mask == 0 or source_mask > 0xFF:
        raise ProtocolError("CPU CAPABILITIES_GET contains an invalid NMI source mask")
    return CpuNmiCapabilities(source_mask=source_mask)


# 解码CPU NMI硬件/ISR快照；不执行轮询、I/O或测试判断。
def decode_snapshot(body: bytes) -> CpuNmiSnapshot:
    if len(body) != SNAPSHOT_STRUCT.size:
        raise ProtocolError("CPU NMI_SNAPSHOT_GET response length is invalid")
    source_raw, source_masked, nmi_mask, nmi_status, event_count = SNAPSHOT_STRUCT.unpack(body)
    return CpuNmiSnapshot(
        source_raw=source_raw,
        source_masked=source_masked,
        nmi_mask=nmi_mask,
        nmi_status=nmi_status,
        event_count=event_count,
    )
