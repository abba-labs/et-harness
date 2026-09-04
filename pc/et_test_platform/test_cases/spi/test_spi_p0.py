# SPI P0基础配置与片内数据通路。
# 职责：以硬件配置读回、完整RX数据和终态验证最小功能。
# 边界：基线及测试过程在Case中显式展开，不用Helper隐藏硬件流程。
# 依赖：SPI/CRG/Resource公共Driver和只读Support。

import pytest

from ...drivers.crg import CrgPeripheral
from ...drivers.spi import SpiClockMode, SpiRole, SpiStatusFlag
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import TIMEOUT_S, basic_config, frame_text, pattern

pytestmark = [pytest.mark.hardware, pytest.mark.ip("spi")]


# 仅返回直接恢复动作；Controller先停，避免Target清理时仍收到外部时钟。
def _cleanup_actions(support, resource):

    return (
        ("DUT SPI IRQ stop", support.dut.spi.irq_capture_stop),
        ("REF SPI IRQ stop", support.ref.spi.irq_capture_stop),
        ("DUT SPI CS release", lambda: support.dut.spi.cs_set(False)),
        ("REF SPI CS release", lambda: support.ref.spi.cs_set(False)),
        (
            "DUT SPI reset",
            lambda: support.crg.reset(CrgPeripheral.SPI, instance=support.dut.spi.instance_id),
        ),
        (
            "REF SPI reset",
            lambda: support.crg.reset(CrgPeripheral.SPI, instance=support.ref.spi.instance_id),
        ),
        ("Resource pool reset", resource.reset),
    )


# 测试 Feature：
# SPI角色、合法分频读回以及模块Enable/Disable。
#
# 测试方法：
# 1. 每个角色及分频节点先复位参与SPI和资源池，再配置关闭的SPI。
# 2. 读取角色、帧宽和分频，依次读取关闭、开启、关闭状态。
#
# 通过条件：
# 1. 配置逐项匹配，Enable序列严格为False、True、False。
@pytest.mark.parametrize("role", tuple(SpiRole))
@pytest.mark.parametrize("divider_node", ("minimum", "middle", "maximum"))
def test_spi_p0_001_config_readback(
    spi_support, resource_driver, record_property, role, divider_node
):

    # 准备：取固件可编程范围，选三个偶数节点，不把Target分频当成线上频率。
    support = spi_support
    spi = support.dut.spi
    limits = support.dut.limits
    divider = {
        "minimum": limits.divider_min,
        "middle": ((limits.divider_min + limits.divider_max) // 4) * 2,
        "maximum": limits.divider_max,
    }[divider_node]
    config = basic_config(support.dut, role=role, divider=divider)

    # 隔离：任何Feature配置前复位两端SPI和整池资源，不复位控制UART或全部GPIO。
    support.crg.reset(CrgPeripheral.SPI, instance=spi.instance_id)
    support.crg.reset(CrgPeripheral.SPI, instance=support.ref.spi.instance_id)
    resource_driver.reset()

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 配置：关闭状态写入角色、帧宽和精确分频，读取真实硬件配置。
        spi.configure(config)
        actual = spi.config_get()
        before = spi.snapshot_get().enabled
        record_property("expected_role", role.name)
        record_property("expected_divider", divider)
        record_observation(
            record_property,
            key="role",
            value=actual.role.name,
            source="dut",
            endpoint="CONFIG.ROLE",
        )
        record_observation(
            record_property,
            key="divider",
            value=actual.divider,
            source="dut",
            endpoint="CONFIG.DIVIDER",
        )

        # 启停：每次命令后独立读取，保存同一ENABLE端点的时间序列。
        spi.enable_set(True)
        enabled = spi.snapshot_get().enabled
        spi.enable_set(False)
        disabled = spi.snapshot_get().enabled
        sequence = [before, enabled, disabled]
        record_observation(
            record_property,
            key="enable_sequence",
            value=sequence,
            source="dut",
            endpoint="CONFIG.ENABLE",
        )

        # 断言：命令成功不代替硬件读回；输入与实际逐项比较。
        assert actual.role == role and actual.divider == divider
        assert actual.frame_bits == config.frame_bits
        assert sequence == [False, True, False]


# 测试 Feature：
# SPI四种CPOL/CPHA模式、全部可编程帧宽及片内Loopback。
#
# 测试方法：
# 1. 每种模式逐一测试所有整数帧宽，每个节点先复位SPI和资源池。
# 2. 分批预装独立Pattern并选CS，按统一Deadline接收完整8帧。
# 3. 保存帧数据及完成状态，检查FIFO没有残留帧。
#
# 通过条件：
# 1. 每节点8帧与独立输入完整一致，BUSY为0、TX_EMPTY为1且无额外RX。
@pytest.mark.parametrize("mode", tuple(SpiClockMode))
def test_spi_p0_002_internal_loopback(spi_support, resource_driver, record_property, mode):

    # 准备：帧宽范围取运行时可编程限制，每组固定验证8个独立输入。
    support = spi_support
    spi = support.dut.spi
    limits = support.dut.limits
    nodes = []

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 矩阵：每种合法整数帧宽都是独立基线，不能仅取两端点代替全部位宽。
        for bits in range(limits.frame_bits_min, limits.frame_bits_max + 1):
            # 隔离：配置前清除两端硬件状态和整池资源。
            support.crg.reset(CrgPeripheral.SPI, instance=spi.instance_id)
            support.crg.reset(CrgPeripheral.SPI, instance=support.ref.spi.instance_id)
            resource_driver.reset()
            expected = pattern(8, bits)
            spi.configure(basic_config(support.dut, mode=mode, bits=bits, loopback=True))
            spi.enable_set(True)
            received = []
            accepted = 0

            # 发送：每批不超过FIFO深度，先预装再选CS，不把写入数当作接收完成数。
            for offset in range(0, len(expected), limits.fifo_depth):
                spi.cs_set(False)
                batch = expected[offset : offset + limits.fifo_depth]
                accepted += spi.write_frames(batch, timeout_s=TIMEOUT_S)
                spi.cs_set(True)
                received.extend(spi.read_exact(len(batch), timeout_s=TIMEOUT_S))

            # 观测：错误状态只显式读一次，避免轮询提前清除错误证据。
            status = spi.error_status_read()
            remaining = spi.snapshot_get().rx_level
            nodes.append(
                {
                    "frame_bits": bits,
                    "expected": list(expected),
                    "actual": received,
                    "status": int(status.flags),
                    "rx_remaining": remaining,
                }
            )
            record_property("nodes", nodes)
            record_property("frame_bits", bits)
            record_property("expected", frame_text(expected))
            record_property("accepted", accepted)
            record_property("received_frames", received)
            record_observation(
                record_property,
                key="rx",
                value=frame_text(received),
                source="dut",
                endpoint="TRANSFER.RX_DATA",
            )
            record_observation(
                record_property,
                key="busy",
                value=bool(status.flags & SpiStatusFlag.BUSY),
                source="dut",
                endpoint="STATUS.BUSY",
            )

            # 比较：完整数量、完整帧值、TX终态和RX残留共同决定节点是否通过。
            assert accepted == len(expected) and tuple(received) == expected
            assert not status.flags & SpiStatusFlag.BUSY
            assert status.flags & SpiStatusFlag.TX_EMPTY
            assert remaining == 0
