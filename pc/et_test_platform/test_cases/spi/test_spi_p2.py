# SPI P2组合与恢复测试。
# 职责：验证真实外部时钟等待、恢复和DMA交互。
# 边界：配置与激励留在Case，Driver仅实现本IP动作和有界等待。
# 依赖：SPI/GPIO/CRG/Resource及本IP只读支持数据。

import time

import pytest

from ...drivers.crg import CrgPeripheral
from ...drivers.dma import DmaIrqEvent
from ...drivers.spi import SpiRole, SpiStatusFlag
from ...drivers.sysctrl import DmaRequestRoute
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    TIMEOUT_S,
    basic_config,
    dma_config,
    frame_text,
    pack_frames,
    pattern,
    unpack_frames,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("spi")]


# 直接关闭两端再复位资源，清理失败由现有聚合器保留，不吞掉Primary Error。
def _cleanup_actions(support, resource):

    return (
        ("Controller stop", lambda: support.dut.spi.enable_set(False)),
        ("Target stop", lambda: support.ref.spi.enable_set(False)),
        (
            "SPI DUT reset",
            lambda: support.crg.reset(CrgPeripheral.SPI, instance=support.dut.spi.instance_id),
        ),
        (
            "SPI REF reset",
            lambda: support.crg.reset(CrgPeripheral.SPI, instance=support.ref.spi.instance_id),
        ),
        ("Resource reset", resource.reset),
    )


# DMA先停止访问，再复位SPI和资源；不能在活动DMA仍持有地址时释放缓冲区。
def _dma_cleanup(support, resource, dma, sysctrl, interfaces):

    return (
        *(
            (f"DMA channel {channel} stop", lambda channel=channel: dma.stop(channel))
            for channel in range(4)
        ),
        *(
            (f"DMA channel {channel} release", lambda channel=channel: dma.deconfigure(channel))
            for channel in range(4)
        ),
        ("DMA controller disable", dma.controller_disable),
        ("DMA reset", lambda: support.crg.reset(CrgPeripheral.DMA, instance=dma.instance_id)),
        *(
            (
                f"route {interface} release",
                lambda interface=interface: sysctrl.release_dma_request(dma.instance_id, interface),
            )
            for interface in interfaces
        ),
        *_cleanup_actions(support, resource),
    )


# 测试 Feature：
# SPI DMA TX/RX水位边界、四通道双向跨FIFO搬运及CPU恢复。
#
# 测试方法：
# 1. 每个节点先复位DMA、两端SPI和资源池，再配置连接文件给出的引脚。
# 2. TX在静止Level上改变阈值；RX先产生R帧，再增加一帧，核对单笔DMA边界。
# 3. 完整传输使用四个硬件握手通道，先两端RX、再Target TX、最后Controller TX。
# 4. 比较两端目的内存与独立Pattern，关闭DMA后再做一笔CPU双向收发。
#
# 通过条件：
# 1. 边界前通道不完成，边界后TRANSFER_DONE且无ERROR；全量及尾帧数据准确。
@pytest.mark.parametrize(
    "scenario", ("tx_empty", "tx_low", "tx_high", "rx_low", "rx_high", "full_even", "full_tail")
)
@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("width_node", ("byte", "maximum"))
def test_spi_p2_001_dma_watermarks(
    spi_support, spi_dma_support, resource_driver, record_property, scenario, reverse, width_node
):

    # 准备：角色、FIFO深度和DMA端点全部由当前连接及芯片映射提供。
    support = spi_support
    dma, sysctrl, mapping = spi_dma_support
    controller, target = (support.ref, support.dut) if reverse else (support.dut, support.ref)
    master, slave = controller.spi, target.spi
    depth = min(controller.limits.fifo_depth, target.limits.fifo_depth)
    bits = min(controller.limits.frame_bits_max, target.limits.frame_bits_max)
    bits = min(8, bits) if width_node == "byte" else bits
    access_bits = mapping.SPI_DMA_ACCESS_BITS
    master_address, master_tx, master_rx = mapping.SPI_DMA_ENDPOINTS[master.instance_id]
    slave_address, slave_tx, slave_rx = mapping.SPI_DMA_ENDPOINTS[slave.instance_id]
    interfaces = mapping.SPI_DMA_INTERFACES[:4]
    count = 2 * depth + (scenario == "full_tail")
    sent, reply = pattern(count, bits), pattern(count, bits, inverse=True)

    # 释放：先停止通道并解除Service配置，再关闭Controller，最后复位。
    for channel in range(4):
        dma.stop(channel)
        dma.deconfigure(channel)
    dma.controller_disable()

    # 隔离：配置前复位DMA、两端SPI和整池资源，不能复用旧DMA地址。
    support.crg.reset(CrgPeripheral.DMA, instance=dma.instance_id)
    support.crg.reset(CrgPeripheral.SPI, instance=master.instance_id)
    support.crg.reset(CrgPeripheral.SPI, instance=slave.instance_id)
    resource_driver.reset()

    with case_cleanup_scope(
        lambda: _dma_cleanup(support, resource_driver, dma, sysctrl, interfaces)
    ):
        # GPIO由独立Driver配置；SPI Service只接收本IP命令。
        for gpio, function in controller.pins:
            support.gpio.configure_signal(gpio, function, master.instance_id)

        # Target的四根引脚同样从连接文件读取。
        for gpio, function in target.pins:
            support.gpio.configure_signal(gpio, function, slave.instance_id)

        # 路由按RX/RX/TX/TX顺序分配，四个不同接口避免请求互相覆盖。
        for interface, request in zip(
            interfaces, (master_rx, slave_rx, slave_tx, master_tx), strict=True
        ):
            sysctrl.configure_route(DmaRequestRoute(dma.instance_id, interface, request))

        # 每个帧单独占一个DMA访问单元；目的区先置非期望值，防止未搬运却相等。
        tx_a = resource_driver.create(count * access_bits // 8)
        tx_b = resource_driver.create(count * access_bits // 8)
        rx_a = resource_driver.create(count * access_bits // 8)
        rx_b = resource_driver.create(count * access_bits // 8)
        resource_driver.write(tx_a, pack_frames(sent, access_bits))
        resource_driver.write(tx_b, pack_frames(reply, access_bits))
        resource_driver.write(rx_a, bytes([0xCD]) * rx_a.size)
        resource_driver.write(rx_b, bytes([0xCD]) * rx_b.size)
        slave.configure(basic_config(target, role=SpiRole.TARGET, bits=bits))
        master.configure(basic_config(controller, bits=bits))
        # Target按SDK初始化序列开放本实例CS通道，再启用移位模块。
        slave.cs_set(True)
        slave.enable_set(True)
        master.enable_set(True)
        dma.controller_enable()
        record_property("scenario", scenario)
        record_property("expected", list(sent))

        # TX水位：没有CS时FIFO不消耗，已Arm通道的变化只能来自阈值变化。
        if scenario.startswith("tx_"):
            tx_max = min(depth - 1, controller.fifo_limits.dma_tx_max)
            level = {"tx_empty": 0, "tx_low": min(1, tx_max), "tx_high": tx_max}[scenario]
            master.write_frames(sent[:level])
            master.dma_configure(True, False, max(0, level - 1), 0)
            dma.configure(
                dma_config(
                    3,
                    interfaces[3],
                    master_address,
                    tx_a,
                    1,
                    receive=False,
                    access_bits=access_bits,
                )
            )
            dma.start(3)

            # 非空节点首先证明低于Level的请求阈值没有提前完成DMA。
            if level:
                before = dma.channel_status(3)
                record_observation(
                    record_property,
                    key="dma_before",
                    value=int(before.interrupt_events),
                    source="dut",
                    endpoint="DMA.TX.EVENTS",
                )
                assert (
                    not before.is_free and not before.interrupt_events & DmaIrqEvent.TRANSFER_DONE
                )
            master.dma_configure(True, False, level, 0)
            states = dma.wait_channels_free((3,), timeout_s=TIMEOUT_S)
            final_level = master.snapshot_get().tx_level
            record_observation(
                record_property,
                key="level",
                value=final_level,
                source="dut",
                endpoint="CONTROLLER.FIFO.TX_LEVEL",
            )
            record_observation(
                record_property,
                key="dma",
                value=int(states[3].interrupt_events),
                source="dut",
                endpoint="DMA.TX.EVENTS",
            )
            assert final_level == level + 1
            assert states[3].interrupt_events & DmaIrqEvent.TRANSFER_DONE
            # 发出已填入的FIFO，独立Target读回证明最后一帧确由DMA写入数据口。
            master.dma_configure(False, False, 0, 0)
            slave.write_frames(reply[: level + 1])
            master.cs_set(True)
            actual = slave.read_exact(level + 1, timeout_s=TIMEOUT_S)
            master.read_exact(level + 1, timeout_s=TIMEOUT_S)
            master.cs_set(False)
            record_observation(
                record_property,
                key="data",
                value=list(actual),
                source="dut",
                endpoint="TARGET.FIFO.RX_DATA",
            )
            assert actual == sent[:level] + sent[:1]
            return

        # RX水位：Target收R帧后保持DMA等待，增加第R+1帧才允许单笔搬运。
        if scenario.startswith("rx_"):
            rx_max = min(depth - 1, target.fifo_limits.dma_rx_max)
            threshold = min(1, rx_max) if scenario == "rx_low" else rx_max
            slave.write_frames(reply[: threshold + 1])
            slave.dma_configure(False, True, 0, threshold)
            dma.configure(
                dma_config(
                    1, interfaces[1], slave_address, rx_b, 1, receive=True, access_bits=access_bits
                )
            )
            dma.start(1)
            master.write_frames(sent[:threshold])
            master.cs_set(True)
            master.read_exact(threshold, timeout_s=TIMEOUT_S)
            before = dma.channel_status(1)
            before_level = slave.snapshot_get().rx_level
            record_observation(
                record_property,
                key="dma_before",
                value=int(before.interrupt_events),
                source="dut",
                endpoint="DMA.RX.EVENTS",
            )
            record_observation(
                record_property,
                key="level",
                value=before_level,
                source="dut",
                endpoint="TARGET.FIFO.RX_LEVEL",
            )
            assert before_level == threshold and not before.is_free
            master.try_write_frame(sent[threshold])
            states = dma.wait_channels_free((1,), timeout_s=TIMEOUT_S)
            actual = unpack_frames(resource_driver.read(rx_b, access_bits // 8), access_bits)
            record_observation(
                record_property,
                key="data",
                value=list(actual),
                source="dut",
                endpoint="DMA.MEMORY.RX",
            )
            record_observation(
                record_property,
                key="dma",
                value=int(states[1].interrupt_events),
                source="dut",
                endpoint="DMA.RX.EVENTS",
            )
            assert actual == sent[:1] and states[1].interrupt_events & DmaIrqEvent.TRANSFER_DONE
            return

        # 双向持续：两端RX先Arm，Target TX先填好FIFO；Controller最后产生时钟。
        configurations = (
            dma_config(
                0, interfaces[0], master_address, rx_a, count, receive=True, access_bits=access_bits
            ),
            dma_config(
                1, interfaces[1], slave_address, rx_b, count, receive=True, access_bits=access_bits
            ),
            dma_config(
                2, interfaces[2], slave_address, tx_b, count, receive=False, access_bits=access_bits
            ),
            dma_config(
                3,
                interfaces[3],
                master_address,
                tx_a,
                count,
                receive=False,
                access_bits=access_bits,
            ),
        )
        master.dma_configure(True, True, min(depth - 1, controller.fifo_limits.dma_tx_max), 0)
        slave.dma_configure(True, True, min(depth - 1, target.fifo_limits.dma_tx_max), 0)

        # 配置四个独立通道，启动顺序按RX/RX/Target TX/Controller TX固定。
        for configuration in configurations:
            dma.configure(configuration)
            dma.start(configuration.channel)
        slave.wait_tx_level(1, timeout_s=TIMEOUT_S)
        master.cs_set(True)
        states = dma.wait_channels_free((0, 1, 2, 3), timeout_s=TIMEOUT_S)
        master.cs_set(False)
        actual_a = unpack_frames(resource_driver.read(rx_a), access_bits)
        actual_b = unpack_frames(resource_driver.read(rx_b), access_bits)
        flags = [int(states[channel].interrupt_events) for channel in (0, 1, 2, 3)]
        record_observation(
            record_property, key="dma", value=flags, source="dut", endpoint="DMA.CHANNEL.EVENTS"
        )
        record_observation(
            record_property,
            key="level",
            value=master.snapshot_get().rx_level,
            source="dut",
            endpoint="CONTROLLER.FIFO.RX_LEVEL",
        )
        record_observation(
            record_property,
            key="data",
            value=[list(actual_a), list(actual_b)],
            source="dut",
            endpoint="DMA.MEMORY.RX",
        )
        assert actual_a == reply and actual_b == sent
        assert all(
            flag & DmaIrqEvent.TRANSFER_DONE and not flag & DmaIrqEvent.ERROR for flag in flags
        )

        # CPU恢复：明确关闭DMA请求和通道，保持SPI配置再发8帧，不复位掩盖残留。
        master.dma_configure(False, False, 0, 0)
        slave.dma_configure(False, False, 0, 0)

        # DMA已完成，先释放四个通道，再关闭Controller，满足Service的独占配置约束。
        for channel in range(4):
            dma.deconfigure(channel)
        dma.controller_disable()
        slave.write_frames(reply[:8])
        master.write_frames(sent[:8])
        master.cs_set(True)
        recovered_a = master.read_exact(8, timeout_s=TIMEOUT_S)
        recovered_b = slave.read_exact(8, timeout_s=TIMEOUT_S)
        master.cs_set(False)
        record_property(
            "cpu_recovery", {"controller": list(recovered_a), "target": list(recovered_b)}
        )
        assert recovered_a == reply[:8] and recovered_b == sent[:8]


# 测试 Feature：
# SPI Target在无SCLK时保持等待，控制命令及时返回，恢复时钟后正常收发。
#
# 测试方法：
# 1. 复位两端及资源，Target预装4帧，Controller配置好但不发时钟。
# 2. 在100ms负向窗口前后读取FIFO与一次性RX，检查TX保持、RX为空。
# 3. 启动Controller恢复双向传输，再独立复位并用不同数据重复一笔。
#
# 通过条件：
# 1. 无时钟时RX不增长，命令不阻塞；恢复和复位后的两笔数据均交叉匹配。
def test_spi_p2_005_no_clock_recovery(spi_support, resource_driver, record_property):

    # 准备：两个不同Pattern轮次，防止上一笔数据残留伪造下一笔PASS。
    support = spi_support
    master, slave = support.dut.spi, support.ref.spi
    config = basic_config(support.dut)
    phases = []

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 两轮：第一轮包含无时钟窗口，第二轮证明重新复位后仍可正常使用。
        for phase in range(2):
            # 隔离：在本轮GPIO和SPI配置之前复位参与实例以及资源池。
            support.crg.reset(CrgPeripheral.SPI, instance=master.instance_id)
            support.crg.reset(CrgPeripheral.SPI, instance=slave.instance_id)
            resource_driver.reset()
            sent = pattern(4, config.frame_bits, inverse=bool(phase))
            reply = pattern(4, config.frame_bits, inverse=not bool(phase))

            # GPIO：先配置Controller，再配置Target，不修改控制UART。
            for gpio, function in support.dut.pins:
                support.gpio.configure_signal(gpio, function, master.instance_id)

            # Target引脚与逻辑handle同样从连接文件读取。
            for gpio, function in support.ref.pins:
                support.gpio.configure_signal(gpio, function, slave.instance_id)

            # 配置：先预装Target返回数据；Controller保持CS未选择，不产生SCLK。
            slave.configure(basic_config(support.ref, role=SpiRole.TARGET, bits=config.frame_bits))
            master.configure(config)
            # Target按SDK初始化序列开放本实例CS通道，再启用移位模块。
            slave.cs_set(True)
            slave.enable_set(True)
            master.enable_set(True)
            slave.write_frames(reply)

            # 负向窗口：明确的100ms无时钟观察，不用睡眠作为传输完成判据。
            if phase == 0:
                before = slave.snapshot_get()
                empty_before = slave.try_read_frame()
                time.sleep(0.1)
                started = time.monotonic()
                empty_after = slave.try_read_frame()
                after = slave.snapshot_get()
                response_ms = (time.monotonic() - started) * 1000
                record_property("response_ms", response_ms)
                record_observation(
                    record_property,
                    key="rx_level",
                    value=after.rx_level,
                    source="dut",
                    endpoint="TARGET.FIFO.RX_LEVEL",
                )
                record_observation(
                    record_property,
                    key="waiting_tx",
                    value=after.tx_level,
                    source="dut",
                    endpoint="TARGET.FIFO.TX_LEVEL",
                )
                assert empty_before is empty_after is None
                assert before.rx_level == after.rx_level == 0
                assert before.tx_level == after.tx_level == len(reply)

            # 恢复：Controller装载并选择CS，双端等待明确的接收帧数，不使用固定延时。
            master.write_frames(sent)
            master.cs_set(True)
            controller_rx = master.read_exact(4, timeout_s=TIMEOUT_S)
            target_rx = slave.read_exact(4, timeout_s=TIMEOUT_S)
            master.cs_set(False)
            controller_status, target_status = master.error_status_read(), slave.error_status_read()
            phases.append(
                {"phase": phase, "controller_rx": list(controller_rx), "target_rx": list(target_rx)}
            )
            record_property("phases", phases)
            record_observation(
                record_property,
                key="rx",
                value=list(controller_rx),
                source="dut",
                endpoint="CONTROLLER.TRANSFER.RX_DATA",
            )
            record_observation(
                record_property,
                key="target_rx",
                value=list(target_rx),
                source="dut",
                endpoint="TARGET.TRANSFER.RX_DATA",
            )
            assert controller_rx == reply and target_rx == sent
            assert not (controller_status.flags | target_status.flags) & SpiStatusFlag.BUSY

        # 两轮原始结果都保留，报告只显示第二次恢复后的完整帧值。
        record_property("last_controller_rx", frame_text(controller_rx))
