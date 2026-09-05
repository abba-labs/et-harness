# ET6801 CAN执行事实。
# 职责：声明已核实的输入时钟和Message RAM元素几何。
# 边界：不选择Case、GPIO、帧ID或测试结果；未知Silicon时钟不猜测。
# 依赖：标准库MappingProxyType；不导入Driver或执行硬件操作。
# 依据：et6x_crg.c的FPGA_VERSION返回40MHz；et6x_can.h的RAM元素大小。

from types import MappingProxyType

# 当前FPGA Driver及历史硅前配置采用40MHz；实际总线速率由外部收发另行验证。
# Silicon时钟源/分频实现尚有文档D04冲突，没有给它伪造一个可用频率。
CAN_CLOCK_HZ = MappingProxyType({"fpga": 40_000_000})

# 两个帧头word、标准过滤一个word、扩展过滤和TX Event各两个word。
CAN_RAM_HEADER_BYTES = 8
CAN_STD_FILTER_BYTES = 4
CAN_EXT_FILTER_BYTES = 8
CAN_EVENT_BYTES = 8

# 三实例控制基址间隔0x8000；SDK将各自前0x4000映射为独立Message RAM。
# UT5覆盖完整16KiB；这里只声明每个实例可测的相对区域，不暴露CPU裸地址给Case。
CAN_RAM_TEST_REGIONS = MappingProxyType(
    {"can0": ((0, 0x4000),), "can1": ((0, 0x4000),), "can2": ((0, 0x4000),)}
)
