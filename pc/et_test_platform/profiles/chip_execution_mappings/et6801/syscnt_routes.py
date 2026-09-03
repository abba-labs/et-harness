# ET6801系统计数器执行事实。
# 职责：记录访问窗口、系统时钟选择、DWT参考和停核观测寄存器。
# 边界：不访问硬件；未确认频率不得进入正式精度断言。
# 依赖：既有HaltSampleSpec与SVD/CMSIS字段定义。

from types import MappingProxyType

from ....programmers import HaltSampleSpec

# CNTCVU→CNTCVL→CNTCVU用于连贯性检查，随后读取CNTSR、CNTCR。
SYSCNT_HALT_SAMPLE = HaltSampleSpec(
    status_address=0xE000EDF0,
    halted_mask=1 << 17,
    register_addresses=(0x4040D004, 0x4040D000, 0x4040D004, 0x4040E004, 0x4040E000),
)

# 两个暂停字段均为bit1；一个是实际状态，一个是策略配置。
SYSCNT_HALT_MASK = 1 << 1
SYSCNT_SOURCE_IDS = (0, 1)

# FPGA SystemCoreClock=25MHz；DWT按CPU周期计数，不使用SYSCNT作为参考。
SYSCNT_REFERENCE_HZ = 25_000_000
SYSCNT_REFERENCE_EVIDENCE = (
    "firmware/chips/et6801/sdk/CMSIS/Device/Source/system_et6x.c:FPGA_VERSION SystemCoreClock"
)

# 当前FPGA两路均为DWT/2；0.1/0.5/1s独立参考诊断确认，不据CNTFID0推算。
# 这是FPGA镜像事实，不宣称Silicon两种振荡源相同或已测得绝对晶振精度。
SYSCNT_CLOCK_HZ = MappingProxyType({0: 12_500_000, 1: 12_500_000})
SYSCNT_CLOCK_EVIDENCE = "artifacts/runs/20260904_syscnt_clock_probe/clock_probe.json"
