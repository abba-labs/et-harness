# UART PC Driver Package 的codec层。
#
# 职责：提供 UART 的Wire Body 纯编码/解码。
# 边界：不访问 TargetClient、Capability/Bench，不等待、不重试、不执行设备 I/O。
# 依赖：仅依赖本 IP Contract/Model、struct 与 ProtocolError。

from __future__ import annotations

import struct
from collections.abc import Iterable

from ...core.errors import ProtocolError
from .models import (
    UartBusyDetectResult,
    UartCapabilities,
    UartCapture,
    UartFeature,
    UartIrqState,
    UartModemStatus,
    UartShadowFifoState,
    UartSnapshot,
    UartStatus,
)
from .validation import bool_byte, uint, validate_line_config

CAPABILITIES = struct.Struct("<5I")
ENDPOINT = struct.Struct("<B3x")
ADDRESS = struct.Struct("<Q")
UART_CONFIG = struct.Struct("<IBBBB")
COUNT = struct.Struct("<I")
POLL_BUDGET = struct.Struct("<I")
READ_REQUEST = struct.Struct("<II")
TRANSFERRED = struct.Struct("<I")
CAPTURE_HEADER = struct.Struct("<B3xII")
UART_SNAPSHOT = struct.Struct("<8I")
UART_STATUS = struct.Struct("<6I")
UART_IRQ_STATE = struct.Struct("<6I")
UART_MODEM_STATUS = struct.Struct("<4I")
LOOPBACK_CONFIG = struct.Struct("<B3x")
FIFO_CONFIG = struct.Struct("<4B")
BUSY_DETECT_RESULT = struct.Struct("<8I")
SHADOW_FIFO_CONFIG = struct.Struct("<4B")
FIFO_ACCESS_CONFIG = struct.Struct("<B3x")
FIFO_TX_VALUE = struct.Struct("<B3x")
FIFO_RX_WRITE = struct.Struct("<4B")
IRQ_CONFIG = struct.Struct("<IBB2x")
NINE_BIT_CONFIG = struct.Struct("<BBH")
MODEM_CONTROL_CONFIG = struct.Struct("<4B")
FLOW_CONTROL_CONFIG = struct.Struct("<4B")
NINE_BIT_REQUEST = struct.Struct("<II")


# 将 encode endpoint 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_endpoint(value: int) -> bytes:

    return ENDPOINT.pack(value)


# 从响应 Body 解码 decode address 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_address(body: bytes) -> int:

    _require_size(body, ADDRESS, "DMA endpoint")
    return ADDRESS.unpack(body)[0]


# 将 encode line config 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_line_config(
    *,
    baudrate: object,
    data_bits: object,
    stop_bits: object,
    parity: object,
) -> bytes:

    values = validate_line_config(
        baudrate=baudrate,
        data_bits=data_bits,
        stop_bits=stop_bits,
        parity=parity,
    )
    return UART_CONFIG.pack(*values, 0)


# 从响应 Body 解码 decode capabilities 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_capabilities(body: bytes) -> UartCapabilities:

    _require_size(body, CAPABILITIES, "CAPABILITIES_GET")
    values = CAPABILITIES.unpack(body)
    return UartCapabilities(UartFeature(values[0]), *values[1:])


# 将单个 uint32 数量字段编码为 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_count(value: int) -> bytes:

    return COUNT.pack(value)


# 将已发布 V1 Wire 的 poll budget 编码为 uint32；该字段只用于兼容，不拥有轮询策略。
def encode_poll_budget(value: int) -> bytes:

    return POLL_BUDGET.pack(value)


# 编码已发布 V1 读取请求；PC 发送兼容 budget，实际 Deadline 与轮询仍由 Driver 负责。
def encode_read_request(length: int, budget: int) -> bytes:

    return READ_REQUEST.pack(length, budget)


# 从响应 Body 解码 decode transferred 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_transferred(body: bytes, maximum: int, label: str) -> int:

    _require_size(body, TRANSFERRED, label)
    value = TRANSFERRED.unpack(body)[0]
    if value > maximum:
        raise ProtocolError(f"UART {label} response exceeds request")
    return value


# 从响应 Body 解码 decode capture 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_capture(body: bytes) -> UartCapture:

    if len(body) < CAPTURE_HEADER.size:
        raise ProtocolError("UART capture response is truncated")
    active, expected, received = CAPTURE_HEADER.unpack_from(body)
    data = bytes(body[CAPTURE_HEADER.size :])
    if active not in (0, 1) or received > expected or len(data) != received:
        raise ProtocolError("UART capture response is inconsistent")
    return UartCapture(bool(active), expected, received, data)


# 从响应 Body 解码 decode snapshot 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_snapshot(body: bytes) -> UartSnapshot:

    _require_size(body, UART_SNAPSHOT, "SNAPSHOT_GET")
    return UartSnapshot(*UART_SNAPSHOT.unpack(body))


# 将 encode bool 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_bool(value: object, name: str) -> bytes:

    if name == "DMA mode":
        return LOOPBACK_CONFIG.pack(uint(value, 8, name))
    return LOOPBACK_CONFIG.pack(bool_byte(value, name))


# 将 encode fifo config 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_fifo_config(
    enabled: object,
    tx_threshold: int,
    rx_threshold: int,
    dma_mode: int,
) -> bytes:

    return FIFO_CONFIG.pack(
        bool_byte(enabled, "FIFO enabled"),
        tx_threshold,
        rx_threshold,
        dma_mode,
    )


# 从响应 Body 解码 decode status 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_status(body: bytes) -> UartStatus:

    _require_size(body, UART_STATUS, "STATUS_GET")
    return UartStatus(*UART_STATUS.unpack(body))


# 将 encode irq config 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_irq_config(mask: int, enabled: object, priority: int) -> bytes:

    return IRQ_CONFIG.pack(mask, bool_byte(enabled, "IRQ enabled"), priority)


# 从响应 Body 解码 decode irq state 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_irq_state(body: bytes) -> UartIrqState:

    _require_size(body, UART_IRQ_STATE, "IRQ_STATE_GET")
    return UartIrqState(*UART_IRQ_STATE.unpack(body))


# 将 encode nine bit config 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_nine_bit_config(
    enabled: object,
    address_match: object,
    address: int,
) -> bytes:

    return NINE_BIT_CONFIG.pack(
        bool_byte(enabled, "9-bit enabled"),
        bool_byte(address_match, "9-bit address match"),
        address,
    )


# 将 encode nine bit write 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_nine_bit_write(values: Iterable[int], budget: int) -> bytes:

    words = tuple(values)
    return NINE_BIT_REQUEST.pack(len(words), budget) + struct.pack(f"<{len(words)}H", *words)


# 从响应 Body 解码 decode nine bit read 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_nine_bit_read(body: bytes, maximum_words: int) -> tuple[int, ...]:

    if len(body) % 2 != 0 or len(body) > maximum_words * 2:
        raise ProtocolError("UART 9-bit read response length is invalid")
    count = len(body) // 2
    if count == 0:
        return ()
    values = struct.unpack(f"<{count}H", body)
    if any(value > 0x1FF for value in values):
        raise ProtocolError("UART 9-bit read response contains a 10-bit value")
    return tuple(values)


# 将 encode flow control 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_flow_control(
    enabled: object,
    rts_polarity: int,
    cts_polarity: int,
) -> bytes:

    return FLOW_CONTROL_CONFIG.pack(
        bool_byte(enabled, "flow control enabled"),
        rts_polarity,
        cts_polarity,
        0,
    )


# 将 encode modem control 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_modem_control(rts: object, dtr: object) -> bytes:

    return MODEM_CONTROL_CONFIG.pack(
        bool_byte(rts, "RTS"),
        bool_byte(dtr, "DTR"),
        0,
        0,
    )


# 从响应 Body 解码 decode modem status 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_modem_status(body: bytes) -> UartModemStatus:

    _require_size(body, UART_MODEM_STATUS, "MODEM_STATUS_GET")
    return UartModemStatus(*UART_MODEM_STATUS.unpack(body))


# 从响应 Body 解码 decode busy detect 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_busy_detect(body: bytes) -> UartBusyDetectResult:

    _require_size(body, BUSY_DETECT_RESULT, "BUSY_DETECT_TRIGGER")
    (
        pre_trigger_usr,
        observed_iir,
        observed_usr,
        trigger_count,
        busy_observed,
        interrupt_observed,
        cleared,
        recovered,
    ) = BUSY_DETECT_RESULT.unpack(body)
    flags = (busy_observed, interrupt_observed, cleared, recovered)
    if any(flag not in (0, 1) for flag in flags):
        raise ProtocolError("UART Busy Detect result contains invalid flags")
    return UartBusyDetectResult(
        pre_trigger_usr=pre_trigger_usr,
        observed_iir=observed_iir,
        observed_usr=observed_usr,
        trigger_count=trigger_count,
        busy_observed=bool(busy_observed),
        interrupt_observed=bool(interrupt_observed),
        cleared=bool(cleared),
        recovered=bool(recovered),
    )


# 将 encode shadow fifo 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_shadow_fifo(
    enabled: object,
    tx_threshold: int,
    rx_threshold: int,
) -> bytes:

    return SHADOW_FIFO_CONFIG.pack(
        bool_byte(enabled, "shadow FIFO enabled"),
        tx_threshold,
        rx_threshold,
        0,
    )


# 从响应 Body 解码 decode shadow fifo 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_shadow_fifo(body: bytes) -> UartShadowFifoState:

    _require_size(body, SHADOW_FIFO_CONFIG, "SHADOW_FIFO_CONFIG")
    enabled, tx_threshold, rx_threshold, reserved = SHADOW_FIFO_CONFIG.unpack(body)
    if reserved != 0 or enabled not in (0, 1):
        raise ProtocolError("UART shadow FIFO response is invalid")
    if tx_threshold not in (0, 2, 4, 8) or rx_threshold not in (1, 4, 8, 14):
        raise ProtocolError("UART shadow FIFO thresholds are invalid")
    return UartShadowFifoState(bool(enabled), tx_threshold, rx_threshold)


# 将 encode fifo access 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_fifo_access(enabled: object) -> bytes:

    return FIFO_ACCESS_CONFIG.pack(bool_byte(enabled, "FIFO access enabled"))


# 从响应 Body 解码 decode fifo access 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_fifo_access(body: bytes) -> bool:

    _require_size(body, FIFO_ACCESS_CONFIG, "FIFO_ACCESS_SET")
    active = FIFO_ACCESS_CONFIG.unpack(body)[0]
    if active not in (0, 1):
        raise ProtocolError("UART FIFO access response is invalid")
    return bool(active)


# 从响应 Body 解码 decode fifo tx 对应事实；严格验证长度/保留字段，协议不一致时抛出 ProtocolError。
def decode_fifo_tx(body: bytes) -> int:

    _require_size(body, FIFO_TX_VALUE, "FIFO_TX_READ")
    value = FIFO_TX_VALUE.unpack(body)[0]
    if body[1:] != b"\x00\x00\x00":
        raise ProtocolError("UART FIFO TX read response is invalid")
    return value


# 将 encode fifo rx 对应字段编码为已发布 Wire Body；仅做纯转换与字段校验，不访问 TargetClient 或设备。
def encode_fifo_rx(
    value: int,
    parity_error: object,
    framing_error: object,
) -> bytes:

    return FIFO_RX_WRITE.pack(
        value,
        bool_byte(parity_error, "FIFO RX parity error"),
        bool_byte(framing_error, "FIFO RX framing error"),
        0,
    )


# 处理 require response size 的纯 Wire 规则；不访问 TargetClient、Capability、Bench 或设备 I/O。
def require_response_size(
    body: bytes,
    expected: int | None,
    command_name: str,
) -> bytes:

    if expected is not None and len(body) != expected:
        raise ProtocolError(
            f"UART {command_name} response length is invalid: expected {expected}, got {len(body)}"
        )
    return bytes(body)


def _require_size(body: bytes, layout: struct.Struct, label: str) -> None:
    if len(body) != layout.size:
        raise ProtocolError(f"UART {label} response length is invalid")
