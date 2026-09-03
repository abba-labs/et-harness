# ET6801 IPCM双核执行映射。
# 职责：声明核间事件端点与真实Peer身份，不把部署资格写进硅Capability。
# 边界：仅提供不可变数据；不访问Target、不执行Case，也不改变其他IP映射。
# 依赖：ET6801历史IPCM测试与本仓库Core1启动Driver。

from types import MappingProxyType

# 历史IPCM_9使用CORE0事件11、CORE1事件10；第二目标事件9供同核多目标测试。
# Core1硬件身份来自DUALCORE_getCurrentCoreId()，不是逻辑CPU下标。
IPCM_EXECUTION_MAPPING = MappingProxyType(
    {
        "local_endpoint": 11,
        "peer_endpoint": 10,
        "peer_secondary_endpoint": 9,
        "peer_executor_identity": 2,
    }
)

IPCM_EXECUTION_EVIDENCE = (
    "ET6801:DFP/Test/FPGATest/ipcm_fpga_test.c:IPCM_9",
    "firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_dualcore.c:DUALCORE_getCurrentCoreId",
    "firmware/chips/et6801/core1_peer/src/et_core1_ipcm_peer.c",
)
