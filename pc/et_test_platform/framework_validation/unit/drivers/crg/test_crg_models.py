# CRG 公共枚举契约测试。
# 职责：验证公共外设类别编号保持稳定，避免 PC 与 Firmware Wire 语义漂移。
# 边界：不执行设备通信、硬件操作或芯片能力判断。
# 依赖：仅依赖 CRG 公共 Driver Model。

from et_test_platform.drivers.crg import CrgPeripheral


# 测试 Feature：CRG 公共外设类别的稳定编号。
#
# 测试方法：逐项读取公开枚举值并与已发布契约比较。
#
# 通过条件：全部已发布类别保持连续且不复用既有编号。
def test_crg_peripheral_values_are_stable() -> None:

    assert int(CrgPeripheral.UART) == 0
    assert int(CrgPeripheral.DMA) == 1
    assert int(CrgPeripheral.AES) == 2
    assert int(CrgPeripheral.CORDIC) == 3
    assert int(CrgPeripheral.FMAC) == 4
    assert int(CrgPeripheral.CRC) == 5
    assert int(CrgPeripheral.STIMER) == 6
    assert int(CrgPeripheral.WDG) == 7
    assert int(CrgPeripheral.IPCM) == 8
    assert int(CrgPeripheral.SPI) == 9
