# SPI P1外部数据、FIFO和错误路径。
# 职责：从连接文件选择双SPI，以明确的配置、刺激和硬件读回验证Feature。
# 边界：GPIO通过独立Driver配置，SPI不承担其他IP初始化。
# 依赖：本IP数据辅助、SPI/GPIO/CRG/Resource Driver和结果记录接口。

from dataclasses import replace

import pytest

from ...drivers.crg import CrgPeripheral
from ...drivers.spi import SpiClockMode, SpiRole, SpiStatusFlag, SpiTransferMode
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import TIMEOUT_S, basic_config, pattern

pytestmark = [pytest.mark.hardware, pytest.mark.ip("spi")]


# 返回当前Case实际持有的两个SPI及Resource的直接恢复动作，不执行测试流程。
def _cleanup_actions(support, resource):

    return (
        ("DUT IRQ stop", support.dut.spi.irq_capture_stop),
        ("REF IRQ stop", support.ref.spi.irq_capture_stop),
        ("DUT SPI disable", lambda: support.dut.spi.enable_set(False)),
        ("REF SPI disable", lambda: support.ref.spi.enable_set(False)),
        (
            "DUT SPI reset",
            lambda: support.crg.reset(CrgPeripheral.SPI, instance=support.dut.spi.instance_id),
        ),
        (
            "REF SPI reset",
            lambda: support.crg.reset(CrgPeripheral.SPI, instance=support.ref.spi.instance_id),
        ),
        ("Resource reset", resource.reset),
    )


# 测试 Feature：
# 双SPI外部全双工、四种模式、位宽边界、角色交换及Target片内回环。
#
# 测试方法：
# 1. 每个节点复位双SPI及资源池，按连接文件通过GPIO Driver设置两端信号。
# 2. Target先装Pattern B，Controller装Pattern A后选择CS，读取两个RX FIFO。
# 3. 交换角色，分别验证外接路径和Target内部Loopback节点。
#
# 通过条件：
# 1. 外接节点双方交叉匹配；Target回环节点等于自身输入，两端BUSY清零且无额外帧。
@pytest.mark.parametrize("mode", tuple(SpiClockMode))
@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("target_loopback", (False, True))
@pytest.mark.parametrize("width_node", ("minimum", "byte", "maximum"))
def test_spi_p1_002_paired_transfer(
    spi_support, resource_driver, record_property, mode, reverse, target_loopback, width_node
):

    # 准备：角色可交换，位宽取两端可编程范围交集；不写死物理handle。
    support = spi_support
    controller, target = (support.ref, support.dut) if reverse else (support.dut, support.ref)
    low = max(controller.limits.frame_bits_min, target.limits.frame_bits_min)
    high = min(controller.limits.frame_bits_max, target.limits.frame_bits_max)
    bits = {"minimum": low, "byte": max(low, min(8, high)), "maximum": high}[width_node]
    count = min(8, controller.limits.fifo_depth, target.limits.fifo_depth)
    sent = pattern(count, bits)
    reply = pattern(count, bits, inverse=True)
    master, slave = controller.spi, target.spi

    # 隔离：第一次配置前复位两端及资源，GPIO只改本Case的八个信号。
    support.crg.reset(CrgPeripheral.SPI, instance=master.instance_id)
    support.crg.reset(CrgPeripheral.SPI, instance=slave.instance_id)
    resource_driver.reset()

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 引脚：先完成全部Pinmux，再启动任何一端，避免输出对打。
        for endpoint in (controller, target):
            # 信号：逐项配置当前实例的CLK、CS、MOSI、MISO，不改其他IP引脚。
            for gpio, function in endpoint.pins:
                support.gpio.configure_signal(gpio, function, endpoint.spi.instance_id)

        # Target：先启用并预装全部返回数据，再让Controller产生SCLK。
        slave.configure(
            basic_config(
                target, role=SpiRole.TARGET, mode=mode, bits=bits, loopback=target_loopback
            )
        )
        slave.enable_set(True)
        target_written = slave.write_frames(reply)

        # Controller：CS未选中时装载输入，选择CS才发起本笔传输。
        master.configure(basic_config(controller, mode=mode, bits=bits))
        master.enable_set(True)
        master_written = master.write_frames(sent)
        master.cs_set(True)
        controller_rx = master.read_exact(count, timeout_s=TIMEOUT_S)
        target_rx = slave.read_exact(count, timeout_s=TIMEOUT_S)
        master.cs_set(False)

        # 观测：两个硬件端点分别留证，不把同芯片Target标为外部设备。
        master_status, slave_status = master.error_status_read(), slave.error_status_read()
        record_property("expected", list(reply if target_loopback else sent))
        record_property("controller_expected", list(reply))
        record_property("target_loopback", target_loopback)
        record_observation(
            record_property,
            key="controller_rx",
            value=list(controller_rx),
            source="dut",
            endpoint=f"{controller.handle}.TRANSFER.RX_DATA",
        )
        record_observation(
            record_property,
            key="target_rx",
            value=list(target_rx),
            source="dut",
            endpoint=f"{target.handle}.TRANSFER.RX_DATA",
        )
        record_observation(
            record_property,
            key="controller_busy",
            value=bool(master_status.flags & SpiStatusFlag.BUSY),
            source="dut",
            endpoint=f"{controller.handle}.STATUS.BUSY",
        )
        record_observation(
            record_property,
            key="target_busy",
            value=bool(slave_status.flags & SpiStatusFlag.BUSY),
            source="dut",
            endpoint=f"{target.handle}.STATUS.BUSY",
        )

        # 断言：Target内部回环不冒充PAD交叉匹配；每个节点均检查数量及收尾。
        assert target_written == master_written == count
        assert target_rx == (reply if target_loopback else sent)
        if not target_loopback:
            assert controller_rx == reply
        assert not (master_status.flags | slave_status.flags) & SpiStatusFlag.BUSY
        assert master.snapshot_get().rx_level == slave.snapshot_get().rx_level == 0


# 测试 Feature：
# SPI TX_RX、TX_ONLY、RX_ONLY、EEPROM_READ及精确接收帧数。
#
# 测试方法：
# 1. 两端复位和GPIO配置后，Target预装返回帧，Controller配置当前传输模式。
# 2. TX_RX/TX_ONLY发送N帧；RX_ONLY发一个启动字；EEPROM_READ发命令后接收N帧。
# 3. 分别采集两端实际帧数及有效方向数据，确认没有额外RX。
#
# 通过条件：
# 1. 有效方向数据正确；只发不接收，只收N帧，命令后读产生N+1帧外部时钟。
@pytest.mark.parametrize("transfer_mode", tuple(SpiTransferMode))
@pytest.mark.parametrize("count_node", ("one", "several"))
def test_spi_p1_003_transfer_modes(
    spi_support, resource_driver, record_property, transfer_mode, count_node
):

    # 准备：EEPROM_READ额外一帧用于命令阶段，全部预装数据不超过两端FIFO。
    support = spi_support
    controller, target = support.dut, support.ref
    master, slave = controller.spi, target.spi
    count = (
        1
        if count_node == "one"
        else min(4, controller.limits.fifo_depth - 1, target.limits.fifo_depth - 1)
    )
    config = basic_config(controller)
    sent, reply = pattern(count, config.frame_bits), pattern(count, config.frame_bits, inverse=True)
    command = sent[0]
    is_eeprom = transfer_mode == SpiTransferMode.EEPROM_READ
    clocks = count + int(is_eeprom)
    master_input = (
        sent if transfer_mode in (SpiTransferMode.TX_RX, SpiTransferMode.TX_ONLY) else (command,)
    )
    slave_input = ((0,) + reply) if is_eeprom else reply

    # 隔离：在帧格式、路由、FIFO配置前建立空硬件和空资源基线。
    support.crg.reset(CrgPeripheral.SPI, instance=master.instance_id)
    support.crg.reset(CrgPeripheral.SPI, instance=slave.instance_id)
    resource_driver.reset()

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 引脚：当前连接文件中的两端独立交由GPIO Service配置。
        for endpoint in (controller, target):
            # 信号：逐项配置当前实例的四个连接信号。
            for gpio, function in endpoint.pins:
                support.gpio.configure_signal(gpio, function, endpoint.spi.instance_id)

        # 配置：Target始终TX_RX；Controller的N使用真实帧数而非寄存器减一编码。
        slave.configure(basic_config(target, role=SpiRole.TARGET, bits=config.frame_bits))
        slave.enable_set(True)
        target_written = slave.write_frames(slave_input)
        master.configure(replace(config, transfer_mode=transfer_mode, frame_count=count))
        master.enable_set(True)
        actual_mode = master.config_get().transfer_mode
        written = master.write_frames(master_input)
        master.cs_set(True)

        # 接收：先等Target实际收到全部时钟，再读Controller有效接收方向。
        target_rx = slave.read_exact(clocks, timeout_s=TIMEOUT_S)
        expected_rx = 0 if transfer_mode == SpiTransferMode.TX_ONLY else count
        controller_rx = master.read_exact(expected_rx, timeout_s=TIMEOUT_S)
        master.cs_set(False)
        status = master.error_status_read()
        record_property("rx_count", len(controller_rx))
        record_property("target_rx", list(target_rx))
        record_property("expected", list(reply))
        record_observation(
            record_property,
            key="mode",
            value=actual_mode.name,
            source="dut",
            endpoint="CONFIG.TRANSFER_MODE",
        )
        record_observation(
            record_property,
            key="rx",
            value=list(controller_rx),
            source="dut",
            endpoint="TRANSFER.RX_DATA",
        )

        # 比较：只检查该模式定义有效的数据方向，数量和终态均独立验证。
        assert written == len(master_input) and target_written == len(slave_input)
        assert actual_mode == transfer_mode
        if expected_rx:
            assert controller_rx == reply
        if transfer_mode in (SpiTransferMode.TX_RX, SpiTransferMode.TX_ONLY):
            assert target_rx == sent
        if is_eeprom:
            assert target_rx[0] == command
        assert not status.flags & SpiStatusFlag.BUSY
        assert master.snapshot_get().rx_level == slave.snapshot_get().rx_level == 0
