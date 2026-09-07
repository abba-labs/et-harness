# CAN Driver软件合同回归。
# 职责：验证Golden Wire、精确响应、显式动作和Deadline传递。
# 边界：不访问CAN盒子、不形成总线硬件测试结果。
# 依赖：pytest、真实CAN/GPIO/CRG Driver与最小Target替身。

import re
from dataclasses import replace
from pathlib import Path
from struct import pack
from types import SimpleNamespace

import pytest
from et_test_platform.core.errors import ProtocolError, RequestTimeout
from et_test_platform.drivers.can import (
    CanBusConfig,
    CanDmuCounters,
    CanDmuElement,
    CanDmuError,
    CanDmuRequest,
    CanDriver,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanHighPriorityStorage,
    CanIrqSource,
    CanLoopback,
    CanOptions,
    CanPhaseTiming,
    CanRamLayout,
    CanRxSource,
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanTxEventType,
    CanTxFrame,
    CanUnmatchedPolicy,
    codec,
    contract,
)
from et_test_platform.drivers.can.contract import CanCommand
from et_test_platform.drivers.crg import CrgPeripheral
from et_test_platform.drivers.crg.codec import encode_reset
from et_test_platform.drivers.gpio import GpioDriver, GpioFunction

TIMING = CanTiming(CanPhaseTiming(2, 31, 8, 8), CanPhaseTiming(1, 15, 4, 4))
OPTIONS = CanOptions(True, True, True, False, False, True, False, 20, 10, 100)


# 测试Feature：DMU单word访问和独立ISR证据Wire；与控制器/ECC无命令混用。
# 测试方法：逐字节验证四个命令、实例归属、首次Raw及retry策略。
# 通过条件：访问/启停不重试，事件查询可重试且不额外请求DMUIR。
def test_dmu_access_capture_golden() -> None:
    error = CanDmuError.TX_READ
    target = TargetStub(
        [
            pack("<I", 0x12345678),
            b"",
            pack("<9I", int(error), int(error), int(error), 1, 0, 0, 7, 0, 2),
            b"",
        ]
    )
    driver = CanDriver(target, 2)
    assert driver.dmu_word_access(CanDmuElement.TX, 0, timeout_s=0.2) == 0x12345678
    driver.dmu_capture_start(error)
    event = driver.dmu_event_get()
    driver.dmu_capture_stop()
    assert event.raw_status == event.masked_status == event.latched_events == error
    assert event.instance_id == 2 and event.event_count == 1 and event.generation == 7
    assert [request["command"] for request in target.requests] == [87, 88, 90, 89]
    assert target.requests[0]["body"] == bytes.fromhex("02 00000000 00000000 00000000 00000000")
    assert target.requests[1]["body"] == pack("<BI", 2, int(error))
    assert [request["retry_safe"] for request in target.requests] == [False, False, True, False]
    assert target.requests[0]["timeout_s"] == 0.2


# 测试Feature：TTS与Filter SYNC写入、独立读回及RX头时间戳有效性。
# 测试方法：Golden检查91～94命令及两种互斥时间戳格式。
# 通过条件：配置写不重试，非消费查询可重试，TSU指针不误当内部时间戳。
def test_dmu_timestamp_control_golden() -> None:
    target = TargetStub(
        [b"", b"", pack("<I", 1), pack("<5I", 0, 0, 1, 3, 2), pack("<5I", 1, 0xABCD, 0, 0, 1)]
    )
    driver = CanDriver(target, 1)
    driver.dmu_timestamp_set(True)
    driver.filter_sync_set(4, True, extended=True)
    assert driver.filter_sync_get(4, extended=True)
    tsu = driver.rx_timestamp_get(0)
    internal = driver.rx_timestamp_get(1)
    assert tsu.internal_timestamp is None and tsu.tsu_pointer == 3 and tsu.index == 2
    assert internal.internal_timestamp == 0xABCD and internal.tsu_pointer is None
    assert [request["command"] for request in target.requests] == [91, 92, 93, 94, 94]
    assert target.requests[1]["body"] == pack("<B3I", 1, 1, 4, 1)
    assert target.requests[2]["body"] == pack("<B2I", 1, 1, 4)
    assert [request["retry_safe"] for request in target.requests] == [
        False,
        False,
        True,
        True,
        True,
    ]


# 非法Boolean、指针和矛盾有效性必须失败，避免Header位被当作时间戳。
@pytest.mark.parametrize(
    "words",
    (
        (2, 0, 0, 0, 0),
        (0, 1, 0, 0, 0),
        (1, 0, 1, 0, 0),
        (0, 0, 1, 16, 0),
        (0, 0, 0, 1, 0),
        (1, 65536, 0, 0, 0),
    ),
)
def test_rx_timestamp_invalid_response(words) -> None:
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack("<5I", *words)]), 0).rx_timestamp_get(0)


# 非法请求必须在传输前拒绝；单次写的返回值不当作硬件错误发生的证据。
def test_dmu_access_capture_input_validation() -> None:
    target = TargetStub()
    driver = CanDriver(target, 0)
    for sources in (CanDmuError.NONE, CanDmuError(1 << 18), CanIrqSource.TX_COMPLETE):
        with pytest.raises(ValueError):
            driver.dmu_capture_start(sources)
    for kwargs in (
        {"word_index": -1},
        {"word_index": True},
        {"word_index": 0, "write": 1},
        {"word_index": 0, "value": 1},
    ):
        with pytest.raises(ValueError):
            driver.dmu_word_access(CanDmuElement.TX, **kwargs)
    assert target.requests == []


# 非法事件位、保留Fault或实例编码不得解释为有效IRQ证据。
@pytest.mark.parametrize(
    "index,value", ((0, 1 << 18), (1, 1 << 18), (2, 1 << 18), (7, 8), (8, 256))
)
def test_dmu_event_response_rejects_reserved(index, value) -> None:
    words = [0] * 9
    words[index] = value
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack("<9I", *words)]), 0).dmu_event_get()


# 测试Feature：独立Non-ISO选择命令及实际Boolean读回。
# 测试方法：逐字节核对Golden请求，注入非法请求值和非法响应。
# 通过条件：只读可重试，写入不重试，无隐式INIT，错误不返回缓存。
def test_non_iso_commands_golden() -> None:

    target = TargetStub([b"", pack("<I", 1), b"", pack("<I", 0)])
    driver = CanDriver(target, 2)
    driver.non_iso_set(True, timeout_s=0.25)
    assert driver.non_iso_get() is True
    driver.non_iso_set(False)
    assert driver.non_iso_get() is False
    assert [request["command"] for request in target.requests] == [57, 58, 57, 58]
    assert [request["body"] for request in target.requests] == [
        bytes.fromhex("02 01000000"),
        b"\x02",
        bytes.fromhex("02 00000000"),
        b"\x02",
    ]
    assert [request["retry_safe"] for request in target.requests] == [False, True, False, True]
    assert target.requests[0]["timeout_s"] == 0.25
    with pytest.raises(ValueError):
        driver.non_iso_set(1)
    assert len(target.requests) == 4
    target.responses = [pack("<I", 2)]
    with pytest.raises(ProtocolError):
        driver.non_iso_get()


# 测试Feature：四个DMU原语的公共Wire、实际读回和副作用边界。
# 测试方法：逐字节Golden比较，响应与请求独立构造，检查读写重试属性。
# 通过条件：不发送隐式DMA配置，端点/选择/计数如实解码，timeout传递不变。
def test_dmu_commands_golden() -> None:
    target = TargetStub(
        [pack("<I", 0x12340280), b"", pack("<I", 0), pack("<5I", 1, 127, 128, 254, 256)]
    )
    driver = CanDriver(target, 2)
    assert driver.dmu_endpoint_get(CanDmuElement.RX0, timeout_s=0.25) == 0x12340280
    driver.dmu_request_set(CanDmuRequest.TX_EVENT)
    assert driver.dmu_request_get() == CanDmuRequest.RX0
    assert driver.dmu_counters_get() == CanDmuCounters(1, 127, 128, 254, 256)
    assert [request["command"] for request in target.requests] == [79, 80, 81, 82]
    assert [request["body"] for request in target.requests] == [
        bytes.fromhex("02 01000000"),
        bytes.fromhex("02 02000000"),
        b"\x02",
        b"\x02",
    ]
    assert [request["retry_safe"] for request in target.requests] == [True, False, True, False]
    assert target.requests[0]["timeout_s"] == 0.25
    for value in (True, -1, 0, 4, "RX0", CanDmuRequest.RX0):
        with pytest.raises(ValueError):
            driver.dmu_endpoint_get(value)
    for value in (True, -1, 0, 3, "RX0", CanDmuElement.RX0):
        with pytest.raises(ValueError):
            driver.dmu_request_set(value)
    assert len(target.requests) == 4


# 测试Feature：DMU CPU镜像命令及明确的时间戳有效性。
# 测试方法：独立构造原始镜像与公共响应，逐字节核对请求而非在PC解释芯片位域。
# 通过条件：三个命令无DMA副作用，index保留未知哨兵，时间戳缺失返回None。
def test_dmu_image_commands_golden() -> None:
    raw = bytes.fromhex("00 00 84 0c 00 00 b8 12 00 01 02 03 04 05 06 07")
    rx_words = (
        0x321,
        12,
        8,
        0,
        0,
        0,
        8,
        0xFFFFFFFF,
        0x03020100,
        0x07060504,
        *([0] * 14),
        0,
        1,
        3,
        1,
        0x87654321,
    )
    event_words = (0x321, 12, 8, 0, 1, 0xAB12, 0xFFFFFFFF, 0, 1, 3, 1, 0xDEADBEEF)
    target = TargetStub(
        [
            pack("<I", len(raw)) + raw.ljust(80, b"\0"),
            pack("<29I", *rx_words),
            pack("<12I", *event_words),
        ]
    )
    driver = CanDriver(target, 2)
    frame = CanTxFrame(
        0x321,
        CanFrameFlags.FD | CanFrameFlags.BRS | CanFrameFlags.STORE_EVENT,
        8,
        0x12,
        bytes(range(8)),
    )
    assert driver.dmu_tx_image_encode(frame, timeout_s=0.2) == raw
    received = driver.dmu_rx_image_decode(1, raw)
    assert received.frame.data == bytes(range(8)) and received.frame.index == 0xFFFFFFFF
    assert not received.internal_timestamp_valid and received.tsu_pointer == 3
    assert received.transferred_timestamp == 0x87654321
    event = driver.dmu_event_image_decode(raw)
    assert event.event.marker == 0xAB12 and event.event.timestamp is None
    assert event.event.tsu_pointer == 3 and event.transferred_timestamp == 0xDEADBEEF
    assert [request["command"] for request in target.requests] == [84, 85, 86]
    assert target.requests[0]["body"] == b"\x02" + pack("<5I", 0, 0x321, 44, 8, 0x12) + bytes(
        range(8)
    ).ljust(64, b"\0")
    assert target.requests[1]["body"] == b"\x02" + pack("<2I", 1, 16) + raw.ljust(80, b"\0")
    assert target.requests[2]["body"] == b"\x02" + pack("<I", 16) + raw.ljust(80, b"\0")
    assert all(request["retry_safe"] for request in target.requests)
    assert target.requests[0]["timeout_s"] == 0.2


# 测试Feature：DMU镜像请求的边界与类型校验。
# 测试方法：空、未对齐、超长以及非bytes输入。
# 通过条件：请求发送前拒绝，不截断、不默认填充输入数据。
@pytest.mark.parametrize("image", [b"", b"x", b"x" * 84, bytearray(8), None])
def test_dmu_image_input_rejected(image) -> None:
    target = TargetStub([])
    driver = CanDriver(target, 0)
    with pytest.raises(ValueError):
        driver.dmu_rx_image_decode(0, image)
    with pytest.raises(ValueError):
        driver.dmu_event_image_decode(image)
    assert not target.requests


# 测试Feature：DMU响应不伪造时间戳、索引或有效负载。
# 测试方法：单字段破坏有效性、填充和长度，并检查ProtocolError。
# 通过条件：拒绝所有矛盾的公共响应，不返回看似完整的CAN帧。
def test_dmu_image_response_rejected() -> None:
    for length in (0, 1, 81, 84):
        with pytest.raises(ProtocolError):
            codec.decode_dmu_tx_image((length, *([0] * 20)))
    with pytest.raises(ProtocolError):
        codec.decode_dmu_tx_image((8, 0, 0, 1, *([0] * 17)))
    good = [
        0x321,
        12,
        8,
        0,
        0,
        0,
        8,
        0xFFFFFFFF,
        0x03020100,
        0x07060504,
        *([0] * 14),
        0,
        1,
        3,
        1,
        9,
    ]
    for index, value in ((7, 0), (24, 1), (25, 0), (26, 16), (27, 0), (3, 1), (10, 1)):
        bad = list(good)
        bad[index] = value
        with pytest.raises(ProtocolError):
            codec.decode_dmu_rx_image(tuple(bad))
    event = [0x321, 12, 8, 0, 1, 0xAB12, 0xFFFFFFFF, 0, 1, 3, 1, 9]
    for index, value in ((6, 0), (7, 1), (8, 0), (9, 16), (10, 0)):
        bad = list(event)
        bad[index] = value
        with pytest.raises(ProtocolError):
            codec.decode_dmu_event_image(tuple(bad))


# 测试Feature：DMU非法响应失败关闭。
# 测试方法：注入保留选择、非法模数、越界计数和错误长度。
# 通过条件：每项抛ProtocolError，不补默认值或返回请求缓存。
@pytest.mark.parametrize("response", [pack("<I", 3), b"", b"\x00" * 8])
def test_dmu_request_response_rejected(response: bytes) -> None:
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([response]), 0).dmu_request_get()


@pytest.mark.parametrize(
    "words",
    [(0, 0, 0, 0, 0), (0, 0, 0, 0, 1), (0, 0, 0, 0, 255), (256, 0, 0, 0, 256), (0, 0, 0, 0)],
)
def test_dmu_counter_response_rejected(words: tuple[int, ...]) -> None:
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack(f"<{len(words)}I", *words)]), 0).dmu_counters_get()


# 测试Feature：DMU首次错误证据不能被自动重试覆盖。
# 测试方法：独立注入每个错误位、错误Boolean和保留位，核对单次请求属性。
# 通过条件：准确还原公共错误语义，非法响应失败关闭且不额外请求。
@pytest.mark.parametrize("bit", range(18))
def test_dmu_status_golden(bit: int) -> None:
    target = TargetStub([pack("<3I", 1 << bit, 1, 0)])
    status = CanDriver(target, 2).dmu_status_consume(timeout_s=0.2)
    assert status.errors == CanDmuError(1 << bit)
    assert status.enabled and not status.transfer_timestamp
    assert len(target.requests) == 1
    assert target.requests[0]["command"] == 83 and target.requests[0]["body"] == b"\x02"
    assert target.requests[0]["retry_safe"] is False
    assert target.requests[0]["timeout_s"] == 0.2


@pytest.mark.parametrize("words", [(1 << 18, 1, 0), (0, 2, 0), (0, 1, 2), (0, 1)])
def test_dmu_status_rejects_malformed(words: tuple[int, ...]) -> None:
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack(f"<{len(words)}I", *words)]), 0).dmu_status_consume()


# 测试Feature：配置写权限与不隐式解锁的仲裁时序写命令。
# 测试方法：核对独立Golden字节和只读重试属性，非法Boolean不能发送。
# 通过条件：三条命令按顺序各执行一次，不隐藏配置动作或返回缓存。
def test_configuration_protection_commands_golden() -> None:

    target = TargetStub([b"", pack("<I", 1), b""])
    driver = CanDriver(target, 2)
    driver.configuration_write_set(False, timeout_s=0.3)
    assert driver.configuration_write_get() is True
    driver.nominal_timing_write(CanPhaseTiming(2, 11, 4, 4))
    assert [request["command"] for request in target.requests] == [54, 55, 56]
    assert target.requests[0]["body"] == bytes.fromhex("02 00000000")
    assert target.requests[2]["body"] == bytes.fromhex("02 02000000 0b000000 04000000 04000000")
    assert [request["retry_safe"] for request in target.requests] == [False, True, False]
    assert target.requests[0]["timeout_s"] == 0.3

    with pytest.raises(ValueError):
        driver.configuration_write_set(1)

    assert len(target.requests) == 3


# 测试Feature：RAM读、写和逐字交换的固定Wire、有效长度、方向及独立读回。
# 测试方法：使用独立64-word响应，检查三条命令；非对齐、空数组与尾部污染均拒绝。
# 通过条件：读可重试、写和交换不可重试；返回旧值而非写入值，无隐式硬件动作。
def test_ram_access_golden_and_bounds() -> None:

    target = TargetStub(
        [pack("<64I", 0x12345678, 0xABCDEF01, *([0] * 62)), b"", pack("<64I", 7, 8, *([0] * 62))]
    )
    driver = CanDriver(target, 2)
    assert driver.ram_words_read(8, 2) == (0x12345678, 0xABCDEF01)
    driver.ram_words_write(12, (10, 20), timeout_s=0.2)
    assert driver.ram_words_exchange(16, (30, 40), descending=True) == (7, 8)
    assert [request["command"] for request in target.requests] == [51, 52, 53]
    assert target.requests[0]["body"] == bytes.fromhex("02 08000000 02000000 00000000")
    assert target.requests[2]["body"] == bytes.fromhex(
        "02 10000000 02000000 01000000 1e000000 28000000"
    ) + bytes(248)
    assert [request["retry_safe"] for request in target.requests] == [True, False, False]

    for offset, count in ((1, 2), (0, 0), (0, 65)):
        with pytest.raises(ValueError):
            driver.ram_words_read(offset, count)

    assert len(target.requests) == 3
    target.responses = [pack("<64I", *([1] * 64))]

    with pytest.raises(ProtocolError, match="padding"):
        driver.ram_words_read(0, 1)


# 测试Feature：单槽完成事件、保留Raw的捕获启动及实际线路证据。
# 测试方法：用独立小端Golden检查三个新增命令；非法Boolean不得发送到目标。
# 通过条件：命令、字段顺序和重试属性准确，旧命令无需改变。
def test_pending_irq_commands_golden() -> None:

    target = TargetStub([b"", b"", pack("<2I", 1, 512)])
    driver = CanDriver(target, 2)
    driver.tx_buffer_irq_set(3, True, timeout_s=0.5)
    driver.irq_capture_pending(
        CanIrqSource.RX_FIFO0_NEW | CanIrqSource.TX_COMPLETE,
        line1_sources=CanIrqSource.TX_COMPLETE,
    )
    assert driver.irq_line_events_get() == (
        CanIrqSource.RX_FIFO0_NEW,
        CanIrqSource.TX_COMPLETE,
    )
    assert [request["command"] for request in target.requests] == [48, 49, 50]
    assert target.requests[0]["body"] == bytes.fromhex("02 03000000 01000000")
    assert target.requests[1]["body"] == bytes.fromhex("02 01020000 00020000")
    assert [request["retry_safe"] for request in target.requests] == [False, False, True]
    assert target.requests[0]["timeout_s"] == 0.5

    with pytest.raises(ValueError):
        driver.tx_buffer_irq_set(3, 1)

    assert len(target.requests) == 3


# 真实Driver解码独立TX读回向量，错误槽号和非零尾部必须拒绝；只读命令允许安全重试。
@pytest.mark.parametrize("fault", (None, "index", "padding", "flags"))
def test_tx_readback_golden(fault) -> None:
    words = [2, 0x321, 0, 8, 0x5A] + [0x44332211, 0x88776655] + [0] * 14
    if fault == "index":
        words[0] = 1
    if fault == "padding":
        words[-1] = 1
    if fault == "flags":
        words[2] = 0x80000000
    target = TargetStub([pack("<21I", *words)])
    if fault:
        with pytest.raises(ProtocolError):
            CanDriver(target, 0).tx_read(2)
    else:
        assert CanDriver(target, 0).tx_read(2) == CanTxFrame(
            0x321, CanFrameFlags.NONE, 8, 0x5A, bytes.fromhex("11 22 33 44 55 66 77 88")
        )
    assert target.requests[0]["command"] == 47
    assert target.requests[0]["retry_safe"] is True


# 测试Feature：ACK查询在同一个Deadline内重试，不重复发送Clock Stop请求。
# 测试方法：先返回反向ACK再返回目标值，用确定性剩余时间检查每次请求。
# 通过条件：只发查询命令，剩余时间递减，超时保留最后实际ACK。
@pytest.mark.parametrize("expected", (False, True))
def test_clock_stop_wait_uses_one_deadline(monkeypatch, expected) -> None:
    from et_test_platform.drivers.can import driver as module

    remaining = iter((0.8, 0.4))
    deadline = SimpleNamespace(remaining_s=lambda: next(remaining), sleep=lambda seconds: None)
    starts = []

    def start(timeout, **kwargs):
        starts.append(timeout)
        return deadline

    monkeypatch.setattr(module, "OperationDeadline", SimpleNamespace(start=start))
    target = TargetStub([pack("<I", int(not expected)), pack("<I", int(expected))])
    assert CanDriver(target, 0).wait_clock_stop_ack(expected, timeout_s=1.0) is expected
    assert starts == [1.0]
    assert [item["command"] for item in target.requests] == [34, 34]
    assert [item["timeout_s"] for item in target.requests] == [0.8, 0.4]


# 测试Feature：任一Raw源有界等待，不消费协议错误寄存器。
# 测试方法：注入两次独立快照及递减时间预算，检查只发送IRQ查询。
# 通过条件：无隐式清除、使能、PSR读取或重发，零源请求失败关闭。
def test_irq_pending_wait_one_deadline(monkeypatch) -> None:
    from et_test_platform.drivers.can import driver as module

    remaining = iter((0.08, 0.04))
    deadline = SimpleNamespace(remaining_s=lambda: next(remaining), sleep=lambda seconds: None)
    monkeypatch.setattr(
        module, "OperationDeadline", SimpleNamespace(start=lambda *a, **k: deadline)
    )
    target = TargetStub([bytes(16), pack("<4I", 1 << 28, 0, 0, 0)])
    driver = CanDriver(target, 0)
    actual = driver.wait_irq_pending(
        CanIrqSource.PROTOCOL_ARBITRATION | CanIrqSource.PROTOCOL_DATA, timeout_s=0.1
    )
    assert actual.raw_status == CanIrqSource.PROTOCOL_DATA
    assert [item["command"] for item in target.requests] == [37, 37]
    assert [item["timeout_s"] for item in target.requests] == [0.08, 0.04]
    with pytest.raises(ValueError):
        driver.wait_irq_pending(CanIrqSource.NONE, timeout_s=0.1)
    assert len(target.requests) == 2


# 测试Feature：Raw等待失败保存末次硬件快照，不假定超时即协议错误。
# 测试方法：首个快照为空，在第一次等待后触发确定性Deadline超时。
# 通过条件：异常保留last，只有一次IRQ查询，未消费PSR。
def test_irq_pending_wait_timeout_keeps_snapshot(monkeypatch) -> None:
    from et_test_platform.drivers.can import driver as module

    def expire(seconds):
        raise RequestTimeout("expired")

    deadline = SimpleNamespace(remaining_s=lambda: 0.1, sleep=expire)
    monkeypatch.setattr(
        module, "OperationDeadline", SimpleNamespace(start=lambda *a, **k: deadline)
    )
    target = TargetStub([bytes(16)])
    with pytest.raises(RequestTimeout, match="last=CanIrqSnapshot"):
        CanDriver(target, 0).wait_irq_pending(CanIrqSource.PROTOCOL_DATA, timeout_s=0.1)
    assert [item["command"] for item in target.requests] == [37]


# 最后一笔ACK仍为0时超时，不插入复位、重新请求或假应答。
def test_clock_stop_wait_timeout_keeps_last_ack(monkeypatch) -> None:
    from et_test_platform.drivers.can import driver as module

    def expire(seconds):
        raise RequestTimeout("deadline expired")

    deadline = SimpleNamespace(remaining_s=lambda: 0.1, sleep=expire)
    monkeypatch.setattr(
        module, "OperationDeadline", SimpleNamespace(start=lambda *a, **k: deadline)
    )
    target = TargetStub([pack("<I", 0)])
    with pytest.raises(RequestTimeout, match="expected=True, last=False"):
        CanDriver(target, 0).wait_clock_stop_ack(True, timeout_s=0.1)
    assert [item["command"] for item in target.requests] == [34]


# 只保存请求参数并返回显式安排的响应，不模拟期望硬件行为。
class TargetStub:
    # 独立响应队列避免请求自动生成期望，空队列为写命令空响应。
    def __init__(self, responses: list[bytes] | None = None) -> None:
        self.responses = list(responses or [])
        self.requests: list[dict] = []

    # 使用与TargetClient相同的返回形状，记录是否错误启用了写操作重试。
    def request(self, service, command, **kwargs):
        self.requests.append({"service": service, "command": command, **kwargs})
        return SimpleNamespace(body=self.responses.pop(0) if self.responses else b""), None


# 独立Golden为前缀实例2及八个实际计数，不借编码函数构造Expected。
def test_timing_golden_and_explicit_actions() -> None:
    target = TargetStub()
    driver = CanDriver(target, 2)
    assert target.requests == []
    driver.timing_set(TIMING, timeout_s=0.5)
    request = target.requests[0]
    assert request["service"] == 0x010C and request["command"] == 4
    assert request["instance_id"] == 2 and request["retry_safe"] is False
    assert request["timeout_s"] == 0.5
    assert request["body"] == bytes.fromhex(
        "02 02000000 1f000000 08000000 08000000 01000000 0f000000 04000000 04000000"
    )
    assert len(target.requests) == 1


# 身份和实际配置均来自响应，不能在Driver返回最后发送值。
def test_independent_readbacks_and_options_golden() -> None:
    target = TargetStub(
        [
            pack("<2I", 0x12345678, 0x87654321),
            pack("<8I", 2, 31, 8, 8, 1, 15, 4, 4),
            pack("<10I", 1, 1, 0, 0, 0, 1, 0, 20, 10, 100),
            pack("<3I", 127, 127, 255),
        ]
    )
    driver = CanDriver(target, 0)
    assert driver.identity_get().revision == 0x12345678
    assert driver.timing_get() == TIMING
    assert driver.options_get() == replace(OPTIONS, automatic_retry=False)
    assert driver.option_limits_get().ram_watchdog_cycles == 255
    assert all(item["retry_safe"] for item in target.requests)
    assert codec.option_words(OPTIONS) == (1, 1, 1, 0, 0, 1, 0, 20, 10, 100)


# 所有命令的短响应和长响应均失败；包括原本应返回空Body的写命令。
@pytest.mark.parametrize("command", list(CanCommand))
def test_response_exact_length(command: CanCommand) -> None:
    size = contract.RESPONSE_WORDS[command] * contract.WORD.size
    with pytest.raises(ProtocolError):
        codec.decode_response(command, bytes(size + 1))
    if size:
        with pytest.raises(ProtocolError):
            codec.decode_response(command, bytes(size - 1))


# 无效请求在Target接收前拒绝，避免协议整数截断或bool冒充计数。
@pytest.mark.parametrize("instance", [-1, 256, True, "0"])
def test_invalid_instance_has_no_io(instance) -> None:
    target = TargetStub()
    with pytest.raises(ValueError):
        CanDriver(target, instance)
    assert target.requests == []


# 关键语义边界：Boolean不得取2，时序不得为0或让SJW超过段长。
def test_invalid_configuration_has_no_io() -> None:
    target = TargetStub()
    driver = CanDriver(target, 0)
    for phase in (CanPhaseTiming(0, 3, 2, 1), CanPhaseTiming(1, 3, 2, 4)):
        with pytest.raises(ValueError):
            driver.timing_set(CanTiming(phase, TIMING.data))
    with pytest.raises(ValueError):
        driver.options_set(replace(OPTIONS, fd_enabled=2))
    with pytest.raises(ValueError):
        driver.initializing_set(1)
    assert target.requests == []


# 读取非法状态必须暴露ProtocolError，不把任意非零值解释成True。
def test_invalid_response_flags_are_rejected() -> None:
    driver = CanDriver(TargetStub([pack("<I", 2)]), 0)
    with pytest.raises(ProtocolError):
        driver.initializing_get()
    with pytest.raises(ProtocolError):
        codec.decode_options((2, 0, 0, 0, 0, 0, 0, 0, 0, 0))
    with pytest.raises(ProtocolError):
        codec.decode_timing((0,) * 8)


# 等待只读INIT，两次读取共享剩余预算，不重新发START/INIT命令。
def test_wait_uses_one_budget_and_only_queries() -> None:
    target = TargetStub([pack("<I", 0), pack("<I", 1)])
    CanDriver(target, 0).wait_initializing(True, timeout_s=0.5)
    assert [item["command"] for item in target.requests] == [2, 2]
    assert 0 < target.requests[1]["timeout_s"] <= target.requests[0]["timeout_s"] <= 0.5


# 真实C头文件与PC命令号逐个一致，不修改公共Frame定义。
def test_command_ids_match_firmware_header() -> None:
    root = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "firmware").is_dir()
    )
    source = (root / "firmware/services/include/et_can_service.h").read_text(encoding="utf-8")
    found = dict(re.findall(r"ET_CAN_COMMAND_(\w+)\s*=\s*(\d+)u", source))
    assert {name: int(value) for name, value in found.items()} == {
        item.name: item.value for item in CanCommand
    }
    assert "#define ET_CAN_SERVICE_ID 0x010Cu" in source


# GPIO和CRG保持独立Service；连接中的物理值不会被CAN Driver私自设置。
def test_can_support_signals_keep_own_service_wire() -> None:
    target = TargetStub()
    gpio = GpioDriver(target)
    gpio.validate_signal(58, GpioFunction.CAN_RX, 0)
    gpio.configure_signal(59, GpioFunction.CAN_TX, 0)
    assert target.requests[0]["service"] == 0x0014
    assert target.requests[0]["body"] == bytes.fromhex("3a00 0700 0000")
    assert target.requests[1]["body"] == bytes.fromhex("3b00 0800 0000")
    assert int(CrgPeripheral.CAN) == 10
    assert encode_reset(int(CrgPeripheral.CAN), 0) == bytes.fromhex("0a000000")


# RAM配置Golden顺序独立列出；GET使用不同的硬件返回，证明没有请求缓存。
def test_ram_layout_codec_and_independent_readback() -> None:
    words = (0, 2, 8, 2, 24, 2, 0, 0, 64, 168, 2, 1, 184, 4, 2, 0, 472, 4, 2, 1, 760, 64, 64, 64)
    layout = CanRamLayout(
        0,
        2,
        8,
        2,
        24,
        2,
        0,
        False,
        64,
        168,
        2,
        1,
        184,
        4,
        2,
        False,
        472,
        4,
        2,
        True,
        760,
        64,
        64,
        64,
    )
    observed = list(words)
    observed[1] = 1
    target = TargetStub([b"", pack("<24I", *observed), pack("<7I", 16384, 128, 64, 32, 64, 32, 64)])
    driver = CanDriver(target, 2)

    driver.ram_layout_set(layout, timeout_s=0.7)
    assert target.requests[0]["body"] == b"\x02" + pack("<24I", *words)
    assert target.requests[0]["command"] == 10
    assert target.requests[0]["retry_safe"] is False
    assert driver.ram_layout_get().std_count == 1
    assert driver.ram_limits_get().ram_bytes == 16384
    assert len(target.requests) == 3

    with pytest.raises(ValueError):
        driver.ram_layout_set(replace(layout, tx_queue=2))
    assert len(target.requests) == 3
    observed[7] = 2
    with pytest.raises(ProtocolError):
        codec.decode_ram_layout(tuple(observed))


# 总线配置与回环都是显式动作；GET直接使用不同的观测响应。
def test_bus_config_and_loopback_wire() -> None:
    config = CanBusConfig(
        False,
        False,
        16,
        CanTimestampSource.INTERNAL,
        CanTimeoutSource.RX1,
        65535,
        True,
        True,
        True,
        CanUnmatchedPolicy.REJECT,
        CanUnmatchedPolicy.RX1,
    )
    words = (0, 0, 16, 1, 3, 65535, 1, 1, 1, 2, 1)
    observed = (1,) + words[1:]
    target = TargetStub([b"", pack("<11I", *observed), b"", pack("<I", 2), pack("<2I", 16, 65535)])
    driver = CanDriver(target, 1)
    driver.bus_config_set(config)
    assert target.requests[0]["body"] == b"\x01" + pack("<11I", *words)
    assert driver.bus_config_get().monitor is True
    driver.loopback_set(CanLoopback.INTERNAL)
    assert target.requests[2]["body"] == bytes.fromhex("0101000000")
    assert driver.loopback_get() is CanLoopback.EXTERNAL
    assert driver.bus_limits_get().timeout_period == 65535
    assert [request["command"] for request in target.requests] == [12, 13, 14, 15, 16]
    assert all(not target.requests[index]["retry_safe"] for index in (0, 2))

    with pytest.raises(ValueError):
        driver.bus_config_set(replace(config, timestamp_source=1))
    with pytest.raises(ValueError):
        driver.loopback_set(1)
    assert len(target.requests) == 5
    with pytest.raises(ProtocolError):
        codec.decode_bus_config((2,) + words[1:])


# TX_WRITE只准备数据、TX_REQUEST才提交；独立Golden验证64-byte FD帧没有结构体布局依赖。
def test_frame_write_request_and_readback_wire() -> None:
    payload = bytes(range(64))
    frame = CanTxFrame(0x123, CanFrameFlags.FD | CanFrameFlags.BRS, 15, 0x5A, payload)
    received = pack("<8I", 0x321, 12, 15, 0x1234, 3, 0, 64, 2) + payload
    target = TargetStub(
        [
            b"",
            b"",
            received,
            b"",
            pack("<7I", 0, 3, 0, 0, 0, 0, 0),
            pack("<5I", 1, 2, 3, 0, 0),
            pack("<2I", 0, 0x80000000),
            b"",
        ]
    )
    driver = CanDriver(target, 0)
    driver.tx_write(1, frame)
    assert target.requests[0]["body"] == b"\x00" + pack("<5I", 1, 0x123, 12, 15, 0x5A) + payload
    assert len(target.requests) == 1
    driver.tx_request(3)
    actual = driver.rx_read(CanRxSource.FIFO0)
    assert actual.identifier == 0x321 and actual.data == payload and actual.index == 2
    driver.rx_fifo_ack(0, actual.index)
    assert driver.tx_status_get().completed == 3
    assert driver.rx_fifo_status_get(0).fill == 1
    assert driver.rx_buffer_status_get().high == 0x80000000
    driver.rx_buffer_ack(0, 0x80000000)
    assert [item["command"] for item in target.requests] == [17, 18, 21, 22, 19, 20, 23, 24]
    assert not any(target.requests[index]["retry_safe"] for index in (0, 1, 3, 7))


# Classic DLC15为8字节、Remote为0；协议元数据与长度矛盾时不能发命令。
def test_frame_lengths_reject_invalid_input_without_io() -> None:
    target = TargetStub()
    driver = CanDriver(target, 0)
    frame = CanTxFrame(0x123, CanFrameFlags.NONE, 15, 0, b"12345678")
    driver.tx_write(0, frame)
    driver.tx_write(0, replace(frame, flags=CanFrameFlags.REMOTE, data=b""))
    for invalid in (
        replace(frame, data=b"123"),
        replace(frame, identifier=0x800),
        replace(frame, flags=CanFrameFlags.BRS),
        replace(frame, flags=CanFrameFlags.FD | CanFrameFlags.REMOTE),
    ):
        with pytest.raises(ValueError):
            driver.tx_write(0, invalid)
    with pytest.raises(ValueError):
        driver.rx_read(CanRxSource.FIFO1, 1)
    with pytest.raises(ValueError):
        driver.tx_request(0)
    assert len(target.requests) == 2


# RX短槽只暴露真实8字节，保留总线DLC15；非法元数据不能被静默转成成功对象。
def test_short_rx_slot_and_invalid_observations() -> None:
    payload_words = tuple(range(16))
    words = (0x123, 4, 15, 0, 0, 1, 8, 0) + payload_words
    actual = codec.decode_rx_frame(words)
    assert actual.dlc == 15 and len(actual.data) == 8 and actual.nonmatching is True
    for bad in (
        (0x123, 4, 0, 0, 0, 0, 1, 0) + payload_words,
        (0x123, 4, 15, 0, 0, 2, 8, 0) + payload_words,
        (0x123, 32, 15, 0, 0, 0, 8, 0) + payload_words,
    ):
        with pytest.raises(ProtocolError):
            codec.decode_rx_frame(bad)


# 等待只观察状态，不自动发送、读取或Ack；每次查询共享同一剩余预算。
def test_frame_waits_only_query_hardware_state() -> None:
    target = TargetStub(
        [
            pack("<7I", 1, 0, 0, 0, 0, 0, 0),
            pack("<7I", 0, 1, 0, 0, 0, 0, 0),
            pack("<5I", 0, 0, 0, 0, 0),
            pack("<5I", 1, 0, 1, 0, 0),
        ]
    )
    driver = CanDriver(target, 0)
    assert driver.wait_tx_complete(1, timeout_s=0.5).completed == 1
    assert driver.wait_rx_available(0, timeout_s=0.5).fill == 1
    assert [request["command"] for request in target.requests] == [19, 19, 20, 20]
    assert target.requests[1]["timeout_s"] <= target.requests[0]["timeout_s"] <= 0.5
    assert target.requests[3]["timeout_s"] <= target.requests[2]["timeout_s"] <= 0.5


# Extended RANGE_NO_MASK请求的Golden独立给出，GET必须返回后续独立观测而非写入缓存。
def test_filter_golden_and_independent_readback() -> None:
    target = TargetStub([b"", pack("<5I", 1, 3, 0x01234567, 0x0ABCDEF0, 0)])
    driver = CanDriver(target, 0)
    config = CanFilter(CanFilterType.RANGE_NO_MASK, CanFilterAction.FIFO1, 0x10000001, 0x1FFFFFFF)
    driver.filter_set(0, config, extended=True, timeout_s=0.25)
    assert target.requests[0]["body"] == bytes.fromhex(
        "00 01000000 00000000 03000000 02000000 01000010 ffffff1f 00000000"
    )
    assert target.requests[0]["command"] == 25 and not target.requests[0]["retry_safe"]
    assert target.requests[0]["timeout_s"] == 0.25
    actual = driver.filter_get(0, extended=True)
    assert actual == CanFilter(CanFilterType.DUAL, CanFilterAction.REJECT, 0x01234567, 0x0ABCDEF0)
    assert target.requests[1]["body"] == bytes.fromhex("00 01000000 00000000")
    assert target.requests[1]["retry_safe"]


# 非法帧格式、范围和Buffer选择在发命令前拒绝，不能静默取低位或改写目的地。
@pytest.mark.parametrize(
    ("extended", "config"),
    [
        (False, CanFilter(CanFilterType.RANGE_NO_MASK, CanFilterAction.FIFO0, 1, 2)),
        (True, CanFilter(CanFilterType.DISABLED, CanFilterAction.DISABLED, 0, 0)),
        (False, CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 2, 1)),
        (False, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x800, 0)),
        (False, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 1, 2, 3)),
        (False, CanFilter(CanFilterType.DUAL, CanFilterAction.BUFFER, 1, 0, 3)),
        (False, CanFilter(CanFilterType.RANGE, CanFilterAction.BUFFER, 1, 2, 3)),
    ],
)
def test_invalid_filter_has_no_request(extended, config) -> None:
    target = TargetStub()
    with pytest.raises(ValueError):
        CanDriver(target, 0).filter_set(0, config, extended=extended)
    assert target.requests == []


# Buffer索引为独立字段，不冒充ID2；扩展掩码读取仍独立于之前的SET。
def test_buffer_filter_and_extended_mask_contract() -> None:
    target = TargetStub([b"", b"", pack("<I", 0x12345678)])
    driver = CanDriver(target, 0)
    driver.filter_set(
        1, CanFilter(CanFilterType.RANGE, CanFilterAction.BUFFER, 0x7FF, 0, 63), extended=False
    )
    assert target.requests[0]["body"] == pack("<B7I", 0, 0, 1, 0, 7, 0x7FF, 0, 63)
    driver.extended_mask_set(0x1FFFFFFF)
    assert target.requests[1]["body"] == pack("<BI", 0, 0x1FFFFFFF)
    assert driver.extended_mask_get() == 0x12345678
    with pytest.raises(ValueError):
        driver.extended_mask_set(0x20000000)
    assert len(target.requests) == 3


# High Priority状态必须保留Filter列表、索引和存储结果，且查询可安全重试。
def test_high_priority_status_contract() -> None:
    target = TargetStub([pack("<4I", 17, 2, 5, 1)])
    actual = CanDriver(target, 0).high_priority_status_get(timeout_s=0.25)
    assert actual.buffer_index == 17
    assert actual.storage == CanHighPriorityStorage.FIFO0
    assert actual.filter_index == 5 and actual.filter_extended
    assert target.requests[0]["command"] == 43
    assert target.requests[0]["body"] == b"\0"
    assert target.requests[0]["retry_safe"] and target.requests[0]["timeout_s"] == 0.25


# 保留值、未知存储类型和非法Filter列表必须失败关闭。
@pytest.mark.parametrize("words", ((0, 4, 0, 0), (0, 0, 0, 2)))
def test_high_priority_status_rejects_invalid_response(words) -> None:
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack("<4I", *words)]), 0).high_priority_status_get()


# TX Event状态、读取和Ack必须保持三个独立命令，并准确标记只读重试属性。
def test_tx_event_fifo_contract() -> None:
    target = TargetStub(
        [
            pack("<5I", 4, 2, 1, 1, 1),
            pack("<7I", 0x123, 0, 8, 0x5678, 1, 0xA5, 2),
            b"",
        ]
    )
    driver = CanDriver(target, 1)

    status = driver.tx_event_status_get(timeout_s=0.4)
    event = driver.tx_event_read(timeout_s=0.3)
    driver.tx_event_ack(event.index, timeout_s=0.2)

    assert status.fill == 4 and status.get_index == 2 and status.put_index == 1
    assert status.full and status.lost
    assert event.identifier == 0x123 and event.flags == CanFrameFlags.NONE
    assert event.dlc == 8 and event.timestamp == 0x5678
    assert event.event_type is CanTxEventType.TRANSMITTED
    assert event.marker == 0xA5 and event.index == 2
    assert [request["command"] for request in target.requests] == [44, 45, 46]
    assert [request["retry_safe"] for request in target.requests] == [True, True, False]
    assert target.requests[2]["body"] == pack("<BI", 1, 2)


# TX Event保留类型、未知帧位、非法Boolean和不一致帧格式必须作为协议错误。
@pytest.mark.parametrize(
    "words",
    (
        (0x123, 0, 8, 0, 0, 0, 0),
        (0x123, 0x80, 8, 0, 1, 0, 0),
        (0x123, 4 | 2, 8, 0, 1, 0, 0),
        (0x123, 8, 8, 0, 1, 0, 0),
    ),
)
def test_tx_event_rejects_invalid_response(words) -> None:
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack("<7I", *words)]), 0).tx_event_read()


# TX Event状态Boolean严格校验，非法Ack索引在PC侧不得截断为u32。
def test_tx_event_status_and_ack_bounds() -> None:
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack("<5I", 0, 0, 0, 2, 0)]), 0).tx_event_status_get()
    target = TargetStub()
    with pytest.raises(ValueError):
        CanDriver(target, 0).tx_event_ack(-1)
    assert target.requests == []


# 未知过滤动作或掩码非法高位不能返回成功，避免报告把损坏数据当有效配置。
def test_invalid_filter_response_fails_closed() -> None:
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack("<5I", 0, 99, 0, 0, 0)]), 0).filter_get(0, extended=False)
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack("<I", 0x20000000)]), 0).extended_mask_get()


# 消费读清状态不允许重试；每个字段由独立Golden提供，不用请求对象制造期望。
def test_protocol_consume_and_scalar_timer_contract() -> None:
    target = TargetStub(
        [
            pack("<15I", 5, 1, 1, 1, 1, 3, 1, 1, 0, 1, 0x34, 0x81, 0x4B, 1, 0x5A),
            pack("<I", 0x1234),
            b"",
            pack("<I", 0xABCD),
            b"",
            pack("<I", 1),
        ]
    )
    driver = CanDriver(target, 0)
    actual = driver.protocol_status_consume(timeout_s=0.2)
    assert actual.last_error.name == "BIT0" and actual.data_last_error.name == "ACK"
    assert actual.bus_off and actual.error_passive and not actual.received_fd
    assert actual.error_log_count == 0x5A and actual.tdc_position == 0x34
    assert driver.timestamp_get() == 0x1234
    driver.timestamp_reset()
    assert driver.timeout_counter_get() == 0xABCD
    driver.clock_stop_set(True)
    assert driver.clock_stop_ack_get()
    assert [entry["command"] for entry in target.requests] == [29, 30, 31, 32, 33, 34]
    assert [entry["retry_safe"] for entry in target.requests] == [
        False,
        True,
        False,
        True,
        False,
        True,
    ]
    assert target.requests[0]["body"] == b"\0" and target.requests[0]["timeout_s"] == 0.2
    assert target.requests[4]["body"] == bytes.fromhex("00 01000000")


# 错误编码、非法Boolean或响应截断必须失败，不能默认解释成无错误。
@pytest.mark.parametrize("index,value", ((0, 8), (1, 4), (5, 8), (4, 2), (13, 2)))
def test_protocol_consume_rejects_invalid_fields(index, value) -> None:
    words = [0] * 15
    words[index] = value
    target = TargetStub([pack("<15I", *words)])
    with pytest.raises(ProtocolError):
        CanDriver(target, 0).protocol_status_consume()
    assert len(target.requests) == 1 and target.requests[0]["retry_safe"] is False


# Clock Stop布尔输入和输出严格校验；拒绝非法请求时完全不访问设备。
def test_clock_stop_boolean_bounds() -> None:
    target = TargetStub()
    with pytest.raises(ValueError):
        CanDriver(target, 0).clock_stop_set(1)
    assert target.requests == []
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack("<I", 2)]), 0).clock_stop_ack_get()


# IRQ控制分别编码Source、Line、Capture和清除；物理IRQn不会进入PC Wire。
def test_irq_control_and_capture_contract() -> None:
    sources = CanIrqSource.RX_FIFO0_NEW | CanIrqSource.TX_COMPLETE
    target = TargetStub(
        [
            b"",
            b"",
            pack("<4I", int(sources), int(sources), int(CanIrqSource.TX_COMPLETE), 3),
            b"",
            b"",
            pack("<8I", int(sources), int(sources), int(sources), 2, 0, 0, 1, 0),
            b"",
            b"",
        ]
    )
    driver = CanDriver(target, 2)

    driver.irq_mask_set(sources, True)
    driver.irq_line_select_set(CanIrqSource.TX_COMPLETE, 1)
    snapshot = driver.irq_snapshot_get()
    driver.irq_clear(CanIrqSource.RX_FIFO0_NEW)
    driver.irq_capture_start(sources, line1_sources=CanIrqSource.TX_COMPLETE)
    event = driver.irq_event_get()
    driver.irq_capture_stop()
    driver.irq_event_reset()

    assert snapshot.enabled_sources == sources and snapshot.enabled_lines == 3
    assert snapshot.line1_sources == CanIrqSource.TX_COMPLETE
    assert event.latched_events == sources and event.event_count == 2
    assert [request["command"] for request in target.requests] == [35, 36, 37, 38, 39, 41, 40, 42]
    assert target.requests[0]["body"] == pack("<B2I", 2, int(sources), 1)
    assert target.requests[4]["body"] == pack(
        "<B2I", 2, int(sources), int(CanIrqSource.TX_COMPLETE)
    )
    assert [request["retry_safe"] for request in target.requests] == [
        False,
        False,
        True,
        False,
        False,
        True,
        False,
        False,
    ]


# 非法Source、Line、Capture子集和固件异常位图均失败关闭，不产生设备请求。
def test_irq_contract_rejects_invalid_values() -> None:
    target = TargetStub()
    driver = CanDriver(target, 0)

    with pytest.raises(ValueError):
        driver.irq_mask_set(CanIrqSource(1 << 30), True)
    with pytest.raises(ValueError):
        driver.irq_line_select_set(CanIrqSource.RX_FIFO0_NEW, 2)
    with pytest.raises(ValueError):
        driver.irq_capture_start(CanIrqSource.RX_FIFO0_NEW, line1_sources=CanIrqSource.TX_COMPLETE)
    assert target.requests == []

    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack("<4I", 1 << 30, 0, 0, 0)]), 0).irq_snapshot_get()
    with pytest.raises(ProtocolError):
        CanDriver(TargetStub([pack("<8I", 0, 0, 1 << 30, 0, 0, 0, 0, 0)]), 0).irq_event_get()
