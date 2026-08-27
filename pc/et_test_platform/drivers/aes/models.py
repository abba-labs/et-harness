# AES PC Driver Package 数据模型。
#
# 职责：定义稳定 AES 枚举及不可变 Capability、Status 和 Result 模型。
# 边界：不执行 Wire 打包、Profile 查询、TargetClient 访问或可变全局状态。
# 依赖：仅依赖 Python 标准库。

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag


# AES 加密或解密方向的稳定 Wire 枚举。
# AES 运算方向枚举，稳定区分加密与解密，Wire 值不会随具体芯片变化。
class AesDirection(IntEnum):
    ENCRYPT = 0
    DECRYPT = 1


# AES-128 与 AES-256 密钥长度的稳定 Wire 枚举。
class AesKeySize(IntEnum):
    AES128 = 0
    AES256 = 1


# AES ECB、CBC 和 CTR 工作模式的稳定 Wire 枚举。
class AesMode(IntEnum):
    ECB = 0
    CBC = 1
    CTR = 2


# AES 无填充、零填充和 PKCS7 填充的稳定 Wire 枚举。
class AesPadding(IntEnum):
    NONE = 0
    ZERO = 1
    PKCS7 = 2


# AES 32-Bit Word 字节序选择的稳定 Wire 枚举。
class AesEndian(IntEnum):
    LITTLE = 0
    BIG = 1


# AES DMA FIFO 与寄存器传输路径的稳定 Wire 枚举。
class AesDmaTransferMode(IntEnum):
    FIFO = 0
    REGISTER = 1


# AES 七类硬件中断源及其组合掩码的稳定 Wire 定义。
class AesIrqEvent(IntFlag):
    OUTPUT_CONFLICT = 1 << 0
    KEY_MISSING = 1 << 1
    IV_MISSING = 1 << 2
    COMPLETE = 1 << 3
    INCOMPLETE_DISABLE = 1 << 4
    DATA_IN_REQ = 1 << 5
    DATA_OUT_REQ = 1 << 6

    ALL = (
        OUTPUT_CONFLICT
        | KEY_MISSING
        | IV_MISSING
        | COMPLETE
        | INCOMPLETE_DISABLE
        | DATA_IN_REQ
        | DATA_OUT_REQ
    )


# AES Service 自报算法、数据路径和测试扩展能力的稳定位集合。
class AesFeature(IntFlag):
    MODULE_ENABLE = 1 << 0
    ENCRYPTION = 1 << 1
    DECRYPTION = 1 << 2
    KEY_128 = 1 << 3
    KEY_256 = 1 << 4
    ECB = 1 << 5
    CBC = 1 << 6
    CTR = 1 << 7
    PADDING = 1 << 8
    IV = 1 << 9
    CTR_COUNTER = 1 << 10
    STATUS = 1 << 11
    INTERRUPTS = 1 << 12
    DMA = 1 << 13
    CPU_REGISTER_PATH = 1 << 14
    DMA_FIFO_PATH = 1 << 15
    IRQ_TRANSFER = 1 << 16
    TIMED_PROCESS = 1 << 17
    TEST_EXTENSIONS = 1 << 18


# AES 中断驱动传输会话的稳定生命周期状态。
# AES 中断传输状态，供上层判断空闲、运行、完成、终止与故障结果。
class AesIrqTransferState(IntEnum):
    IDLE = 0
    ACTIVE = 1
    COMPLETE = 2
    ABORTED = 3
    FAULT = 4


# 保存一次 AES 配置请求的算法、字节序和 DMA 模式事实。
@dataclass(frozen=True, slots=True)
class AesConfig:
    direction: AesDirection
    key_size: AesKeySize
    mode: AesMode
    padding: AesPadding = AesPadding.NONE
    endian: AesEndian = AesEndian.BIG
    dma_transfer_mode: AesDmaTransferMode = AesDmaTransferMode.REGISTER
    ctr_counter: int = 0


# 保存固件自报的 AES Feature、选项掩码和运行范围上限。
@dataclass(frozen=True, slots=True)
class AesCapabilities:
    api_version: int
    features: AesFeature
    block_size_bytes: int
    hardware_data_length_bits: int
    max_process_bytes: int
    max_process_output_bytes: int
    key_size_mask: int
    mode_mask: int
    padding_mask: int
    endian_mask: int
    dma_mode_mask: int
    irq_event_mask: AesIrqEvent
    irq_transfer_supported: bool
    timed_process_supported: bool


# 保存 AES Busy、输入请求、输出请求和完成状态事实。
@dataclass(frozen=True, slots=True)
class AesStatus:
    busy: bool
    data_in_request: bool
    data_out_request: bool
    finish: bool


# 保存 AES IRQ 原始、有效、锁存和回调计数证据。
@dataclass(frozen=True, slots=True)
class AesIrqSnapshot:
    raw: AesIrqEvent
    status: AesIrqEvent
    latched: AesIrqEvent
    event_count: int
    unexpected_count: int
    overflow_count: int
    generation: int


# 保存 AES PROCESS 的实际输出长度及返回状态。
@dataclass(frozen=True, slots=True)
class AesProcessResult:
    produced_bytes: int
    status: AesStatus


# 保存 AES 中断传输状态、进度、产出和故障事实。
@dataclass(frozen=True, slots=True)
class AesIrqTransferStatus:
    state: AesIrqTransferState
    input_offset: int
    output_offset: int
    produced_bytes: int
    fault_flags: int
    block_count: int


# 保存 AES 目标侧计时、处理字节数和完成状态事实。
@dataclass(frozen=True, slots=True)
class AesTimedResult:
    elapsed_cycles: int
    produced_bytes: int
    measured_bytes: int
    status: AesStatus
