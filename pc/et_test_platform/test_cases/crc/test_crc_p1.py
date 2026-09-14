# CRC P1：显式复位 -> 原硬件配置/刺激 -> 真实读回与独立判定。
# 只读向量在 _p1_vectors；记录与固定退出在 Fixture，不隐藏硬件动作。
from __future__ import annotations

import pytest

from ...drivers.crc import CrcInputAccessWidth, CrcIrqEvent, CrcMode, CrcXorOut
from ._p1_vectors import CRC8_IRQ, CRC32_SWAP, p1_vector

pytestmark = [
    pytest.mark.hardware, pytest.mark.ip("crc"), pytest.mark.usefixtures("crc_p1_evidence"),
]


# Polynomial：原三个多项式、32-byte 输入、精确结果与 Length=0。
@pytest.mark.parametrize("polynomial", (0x04C11DB7, 0x1EDC6F41, 0xA833982B))
def test_crc_p1_001_programmable_polynomial(crc0, resource_driver, polynomial) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_001", polynomial=polynomial)
    source = resource_driver.create(len(vector.payload), alignment=4)
    resource_driver.write(source, vector.payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    measured = crc_handle.calculate(source.address, len(vector.payload))
    assert measured.result == vector.expected
    assert measured.remaining_input_count == 0


# Seed：三个原种子分别独立配置，不继承上一个参数的 Result。
@pytest.mark.parametrize("initial_value", (0x00000000, 0xFFFFFFFF, 0x13579BDF))
def test_crc_p1_002_initial_seed(crc0, resource_driver, initial_value) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_002", initial_value=initial_value)
    source = resource_driver.create(len(vector.payload), alignment=4)
    resource_driver.write(source, vector.payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    measured = crc_handle.calculate(source.address, len(vector.payload))
    assert measured.result == vector.expected
    assert measured.remaining_input_count == 0


# ByteSwap：保留 CRC16/32 × Off/On 及原非对称输入，不以“结果不同”代替 Golden。
@pytest.mark.parametrize(
    ("mode", "byte_swap"),
    ((CrcMode.CRC16, False), (CrcMode.CRC16, True),
     (CrcMode.CRC32, False), (CrcMode.CRC32, True)),
)
def test_crc_p1_003_byte_swap(crc0, resource_driver, mode, byte_swap) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_003", mode=mode, byte_swap=byte_swap)
    source = resource_driver.create(len(vector.payload), alignment=4)
    resource_driver.write(source, vector.payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    measured = crc_handle.calculate(source.address, len(vector.payload))
    assert measured.result == vector.expected
    assert measured.remaining_input_count == 0


# RefIn：逐字节反转的原两组输入语义及结果精确相等。
@pytest.mark.parametrize("ref_in", (False, True))
def test_crc_p1_004_ref_in(crc0, resource_driver, ref_in) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_004", ref_in=ref_in)
    source = resource_driver.create(len(vector.payload), alignment=4)
    resource_driver.write(source, vector.payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    measured = crc_handle.calculate(source.address, len(vector.payload))
    assert measured.result == vector.expected
    assert measured.remaining_input_count == 0


# RefOut：原 CRC16/15-byte 输入，保留单独的结果宽度检查。
@pytest.mark.parametrize("ref_out", (False, True))
def test_crc_p1_005_ref_out(crc0, resource_driver, ref_out) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_005", ref_out=ref_out)
    source = resource_driver.create(len(vector.payload), alignment=4)
    resource_driver.write(source, vector.payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    measured = crc_handle.calculate(source.address, len(vector.payload))
    assert measured.result == vector.expected
    assert measured.result <= 0xFFFF
    assert measured.remaining_input_count == 0


# XorOut：按原 CRC16 自然宽度比较 ALL_ZERO/ALL_ONE。
@pytest.mark.parametrize("xor_out", tuple(CrcXorOut))
def test_crc_p1_006_xor_out(crc0, resource_driver, xor_out) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_006", xor_out=xor_out)
    source = resource_driver.create(len(vector.payload), alignment=4)
    resource_driver.write(source, vector.payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    measured = crc_handle.calculate(source.address, len(vector.payload))
    assert measured.result == vector.expected
    assert measured.result <= 0xFFFF
    assert measured.remaining_input_count == 0


# Length：编程读回在 Calculate 之前；CRC32 四种 remainder 与 CRC16 奇偶均保留。
@pytest.mark.parametrize(
    ("mode", "length_bytes"),
    ((CrcMode.CRC32, 8), (CrcMode.CRC32, 9), (CrcMode.CRC32, 10),
     (CrcMode.CRC32, 11), (CrcMode.CRC16, 8), (CrcMode.CRC16, 9)),
)
def test_crc_p1_007_arbitrary_byte_length(crc0, resource_driver, mode, length_bytes) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_007", mode=mode, length_bytes=length_bytes)
    unit_bytes = int(mode) // 8
    expected_input_count = length_bytes // unit_bytes + length_bytes % unit_bytes
    source = resource_driver.create(length_bytes, alignment=4)
    resource_driver.write(source, vector.payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    crc_handle.data_length_set(length_bytes)
    programmed_count = crc_handle.remaining_input_count_get()
    assert programmed_count == expected_input_count
    measured = crc_handle.calculate(source.address, length_bytes)
    assert measured.result == vector.expected
    assert measured.remaining_input_count == 0


# ALR：两块独立输入先准备好，只写一次 LENGTH，中途不能 reset/reconfigure。
def test_crc_p1_008_auto_length_reload(crc0, resource_driver) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_008")
    first_source = resource_driver.create(64, alignment=4)
    second_source = resource_driver.create(64, alignment=4)
    resource_driver.write(first_source, vector.payload)
    resource_driver.write(second_source, vector.second_payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    crc_handle.data_length_set(len(vector.payload))
    first = crc_handle.calculate(first_source.address, 64)
    assert first.result == vector.expected
    assert first.remaining_input_count == len(vector.payload) // 4
    second = crc_handle.calculate(second_source.address, 64)
    assert second.result == vector.second_expected
    assert second.remaining_input_count == len(vector.second_payload) // 4


# CHECK 匹配：保留清旧 Pending、写 CHECK、计算和当前 Raw/Status 的原顺序。
def test_crc_p1_009_check_match(crc0, resource_driver) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_009")
    event = CrcIrqEvent.CHECK_ERROR
    source = resource_driver.create(len(vector.payload), alignment=4)
    resource_driver.write(source, vector.payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    crc_handle.irq_clear(CrcIrqEvent.ALL)
    crc_handle.check_value_set(vector.expected)
    measured = crc_handle.calculate(source.address, len(vector.payload))
    snapshot = crc_handle.irq_snapshot_get()
    assert measured.result == vector.expected
    assert snapshot.raw & event == CrcIrqEvent.NONE
    assert snapshot.status & event == CrcIrqEvent.NONE


# CHECK 不匹配：自然计算触发错误，不能替换成 Force；ISR 恰好一次且源精确。
def test_crc_p1_010_check_mismatch_irq(crc0, resource_driver) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_010")
    event = CrcIrqEvent.CHECK_ERROR
    source = resource_driver.create(len(vector.payload), alignment=4)
    resource_driver.write(source, vector.payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    crc_handle.irq_clear(CrcIrqEvent.ALL)
    crc_handle.irq_enable(event)
    crc_handle.irq_unmask(event)
    before = crc_handle.irq_snapshot_get()
    crc_handle.check_value_set(vector.expected ^ 0x1)
    measured = crc_handle.calculate(source.address, len(vector.payload))
    after = crc_handle.irq_snapshot_get()
    assert measured.result == vector.expected
    assert after.event_count == before.event_count + 1
    assert after.last_event == event
    assert after.last_raw == event


# FIFO Overflow：七次写入仍为同一目标端 Burst；保留 Disable/Enable 恢复而非 CRG reset。
def test_crc_p1_012_fifo_overflow_recovery(crc0, resource_driver) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_012")
    crc_handle.enable()
    crc_handle.configure(vector.config)
    before = crc_handle.fifo_status_get()
    overflowed = crc_handle.test_input_burst_32((0x12345678,) * 7, checkpoint_count=0)
    crc_handle.disable()
    resource_driver.reset()
    source = resource_driver.create(len(vector.payload), alignment=4)
    resource_driver.write(source, vector.payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    recovery = crc_handle.calculate(source.address, len(vector.payload))
    assert not before.overflow
    assert overflowed.overflow
    assert recovery.result == vector.expected
    assert recovery.remaining_input_count == 0


# Enable -> Disable 连续对照：Disabled 后的新 Force 不得增加回调，保留最后 Clear。
@pytest.mark.parametrize(
    "event", (CrcIrqEvent.BUS_ERROR, CrcIrqEvent.LENGTH_ERROR, CrcIrqEvent.CHECK_ERROR),
)
def test_crc_p1_013_irq_force_delivery(crc0, event) -> None:
    crc_handle = crc0
    crc_handle.reset()
    crc_handle.enable()
    crc_handle.configure(CRC8_IRQ)
    crc_handle.irq_clear(CrcIrqEvent.ALL)
    crc_handle.irq_enable(event)
    crc_handle.irq_unmask(event)
    before = crc_handle.irq_snapshot_get()
    crc_handle.irq_force(event)
    delivered = crc_handle.irq_snapshot_get()
    assert delivered.event_count == before.event_count + 1
    assert delivered.last_event == event
    assert delivered.last_raw == event
    crc_handle.irq_clear(event)
    crc_handle.irq_disable(event)
    disabled_before = crc_handle.irq_snapshot_get()
    crc_handle.irq_force(event)
    disabled_after = crc_handle.irq_snapshot_get()
    assert disabled_after.event_count == disabled_before.event_count
    crc_handle.irq_clear(event)


# Clear：保留三个快照和六项精确判断；Raw、Status、回调计数不能混为一个结果。
def test_crc_p1_014_irq_clear(crc0) -> None:
    crc_handle = crc0
    crc_handle.reset()
    event = CrcIrqEvent.BUS_ERROR
    crc_handle.enable()
    crc_handle.configure(CRC8_IRQ)
    crc_handle.irq_clear(CrcIrqEvent.ALL)
    crc_handle.irq_enable(event)
    crc_handle.irq_mask(event)
    before = crc_handle.irq_snapshot_get()
    crc_handle.irq_force(event)
    pending = crc_handle.irq_snapshot_get()
    crc_handle.irq_clear(event)
    cleared = crc_handle.irq_snapshot_get()
    assert pending.raw == event
    assert pending.status == CrcIrqEvent.NONE
    assert pending.event_count == before.event_count
    assert cleared.raw == CrcIrqEvent.NONE
    assert cleared.status == CrcIrqEvent.NONE
    assert cleared.event_count == before.event_count


# Mask -> Clear -> Unmask -> 新 Force：同一会话连续观察，不插入额外复位。
def test_crc_p1_015_irq_mask_raw_status(crc0) -> None:
    crc_handle = crc0
    crc_handle.reset()
    event = CrcIrqEvent.LENGTH_ERROR
    crc_handle.enable()
    crc_handle.configure(CRC8_IRQ)
    crc_handle.irq_clear(CrcIrqEvent.ALL)
    crc_handle.irq_enable(event)
    crc_handle.irq_mask(event)
    baseline = crc_handle.irq_snapshot_get()
    crc_handle.irq_force(event)
    masked = crc_handle.irq_snapshot_get()
    assert masked.raw == event
    assert masked.status == CrcIrqEvent.NONE
    assert masked.event_count == baseline.event_count
    crc_handle.irq_clear(event)
    crc_handle.irq_unmask(event)
    crc_handle.irq_force(event)
    delivered = crc_handle.irq_snapshot_get()
    assert delivered.event_count == baseline.event_count + 1
    assert delivered.last_event == event
    assert delivered.last_raw == event


# LENGTH=0 后写合法 32-bit 输入，错误必须来自硬件，不是 PC 参数拒绝或 Force。
def test_crc_p1_016_length_error_irq(crc0) -> None:
    crc_handle = crc0
    crc_handle.reset()
    event = CrcIrqEvent.LENGTH_ERROR
    crc_handle.enable()
    crc_handle.configure(CRC32_SWAP)
    crc_handle.irq_clear(CrcIrqEvent.ALL)
    crc_handle.irq_enable(event)
    crc_handle.irq_unmask(event)
    before = crc_handle.irq_snapshot_get()
    crc_handle.data_length_set(0)
    crc_handle.test_input_write(CrcInputAccessWidth.BITS_32, 0x12345678)
    after = crc_handle.irq_snapshot_get()
    assert after.event_count == before.event_count + 1
    assert after.last_event == event
    assert after.last_raw == event


# 合法输入 -> 非法宽度 -> Disable/Enable 后正常 CRC8：三段状态链必须在同一 Case。
def test_crc_p1_018_bus_error_irq_recovery(crc0, resource_driver) -> None:
    crc_handle = crc0
    crc_handle.reset()
    vector = p1_vector("crc_p1_018")
    event = CrcIrqEvent.BUS_ERROR
    crc_handle.enable()
    crc_handle.configure(vector.config)
    crc_handle.irq_clear(CrcIrqEvent.ALL)
    crc_handle.irq_enable(event)
    crc_handle.irq_unmask(event)
    crc_handle.data_length_set(1)
    legal_before = crc_handle.irq_snapshot_get()
    crc_handle.test_input_write(CrcInputAccessWidth.BITS_8, 0x12)
    legal_after = crc_handle.irq_snapshot_get()
    assert legal_after.event_count == legal_before.event_count
    assert legal_after.raw & event == CrcIrqEvent.NONE
    assert legal_after.status & event == CrcIrqEvent.NONE
    crc_handle.data_length_set(1)
    crc_handle.test_input_write(CrcInputAccessWidth.BITS_32, 0x12345678)
    error_after = crc_handle.irq_snapshot_get()
    assert error_after.event_count == legal_after.event_count + 1
    assert error_after.last_event == event
    assert error_after.last_raw == event
    crc_handle.disable()
    resource_driver.reset()
    source = resource_driver.create(len(vector.payload), alignment=4)
    resource_driver.write(source, vector.payload)
    crc_handle.enable()
    crc_handle.configure(vector.config)
    recovery = crc_handle.calculate(source.address, len(vector.payload))
    assert recovery.result == vector.expected
    assert recovery.remaining_input_count == 0
