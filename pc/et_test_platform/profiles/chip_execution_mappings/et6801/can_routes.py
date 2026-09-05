# ET6801 CAN执行事实。
# 职责：声明已核实的输入时钟和Message RAM元素几何。
# 边界：不选择Case、GPIO、帧ID或测试结果；未知Silicon时钟不猜测。
# 依赖：标准库MappingProxyType；不导入Driver或执行硬件操作。
# 依据：et6x_crg.c的FPGA_VERSION返回40MHz；et6x_can.h的RAM元素大小。

from types import MappingProxyType

# mttcan_cfg.svd：NBTP reset=0x06000A03，四字段按实际值=编码+1。
# 这里只声明可独立核验的复位事实，不读取当前设备来生成Expected。
CAN_RESET_NOMINAL_TIMING = (1, 11, 4, 4)
CAN_RESET_INITIALIZING = True
CAN_RESET_FD_ENABLED = False
CAN_ENDIAN_SIGNATURE = 0x87654321

# 当前FPGA Driver及历史硅前配置采用40MHz；实际总线速率由外部收发另行验证。
# Silicon时钟源/分频实现尚有文档D04冲突，没有给它伪造一个可用频率。
CAN_CLOCK_HZ = MappingProxyType({"fpga": 40_000_000})

# 两个帧头word、标准过滤一个word、扩展过滤和TX Event各两个word。
CAN_RAM_HEADER_BYTES = 8
CAN_STD_FILTER_BYTES = 4
CAN_EXT_FILTER_BYTES = 8
CAN_EVENT_BYTES = 8

# 三实例控制基址间隔0x8000；SDK各自前0x4000是CPU访问窗口，不代表独占RAM。
# UT5覆盖单实例16KiB；这里只声明单实例可测范围，不推导并存时物理独立。
CAN_RAM_TEST_REGIONS = MappingProxyType(
    {"can0": ((0, 0x4000),), "can1": ((0, 0x4000),), "can2": ((0, 0x4000),)}
)

# UT6使用各实例不同的相对偏移；20260905 HIL同偏移Filter出现最后实例覆盖。
# 并存按共享16KiB预算划三段4KiB，剩余4KiB不占用；布局及Guard均限制在各段内。
# 这是同时使用时的安全分配，不表示每个控制器的硬件容量仅4KiB。
CAN_CONCURRENT_RAM_REGIONS = MappingProxyType(
    {"can0": (0, 0x1000), "can1": (0x1000, 0x1000), "can2": (0x2000, 0x1000)}
)
