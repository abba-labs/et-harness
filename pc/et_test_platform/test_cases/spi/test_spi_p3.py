# SPI P3连续DMA传输测试。
# 职责：保持SPI配置完成20轮四通道双向搬运，逐轮保存真实硬件结果。
# 边界：不重试失败轮次、不复位掩盖错误、不调用其他Case。
# 依赖：SPI/GPIO/DMA/SYSCTRL/CRG/Resource公共Driver及本IP只读映射。

import pytest

from ...drivers.crg import CrgPeripheral
from ...drivers.dma import DmaIrqEvent
from ...drivers.spi import SpiClockMode, SpiRole, SpiStatusFlag
from ...drivers.sysctrl import DmaRequestRoute
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import TIMEOUT_S, basic_config, dma_config, pack_frames, pattern, unpack_frames

pytestmark = [pytest.mark.hardware, pytest.mark.ip("spi")]


# 先复位DMA终止内存访问，再释放路由、SPI和资源；不把恢复动作当成测试成功。
def _cleanup_actions(support, resource, dma, sysctrl, interfaces):

    return (
        ("DMA reset", lambda: support.crg.reset(CrgPeripheral.DMA, instance=dma.instance_id)),
        *(
            (
                f"route {interface} release",
                lambda interface=interface: sysctrl.release_dma_request(dma.instance_id, interface),
            )
            for interface in interfaces
        ),
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


# 测试 Feature：
# SPI MODE1、8-bit、四DMA通道连续双向收发。
#
# 测试方法：
# 1. 开始前复位DMA、两端SPI及资源池，配置四线连接与四个DMA请求路由。
# 2. 连续20轮，每轮两端各32帧；每轮更换独立Pattern并污染目的缓冲区。
# 3. 先Arm两个RX，再Target TX、Controller TX；选择CS后等待四通道完成。
# 4. 逐轮读回两端目的内存、DMA完成/错误和SPI状态，不在轮间复位SPI。
#
# 通过条件：
# 1. 20轮数据均与对端当轮Pattern相同；四通道完成、没有DMA/SPI错误及残留帧。
def test_spi_p3_002_continuous_dma(spi_support, spi_dma_support, resource_driver, record_property):

    # 准备：实例、引脚、数据端点和DMA访问宽度来自当前连接与执行映射。
    support = spi_support
    dma, sysctrl, mapping = spi_dma_support
    master, slave = support.dut.spi, support.ref.spi
    interfaces = mapping.SPI_DMA_INTERFACES[:4]
    address_a, tx_request_a, rx_request_a = mapping.SPI_DMA_ENDPOINTS[master.instance_id]
    address_b, tx_request_b, rx_request_b = mapping.SPI_DMA_ENDPOINTS[slave.instance_id]
    access_bits = mapping.SPI_DMA_ACCESS_BITS
    count, rounds, history = 32, 20, []

    # 隔离：仅开始时复位全部参与IP和整池资源，连续传输中不靠复位修复错误。
    support.crg.reset(CrgPeripheral.DMA, instance=dma.instance_id)
    support.crg.reset(CrgPeripheral.SPI, instance=master.instance_id)
    support.crg.reset(CrgPeripheral.SPI, instance=slave.instance_id)
    resource_driver.reset()

    with case_cleanup_scope(
        lambda: _cleanup_actions(support, resource_driver, dma, sysctrl, interfaces)
    ):
        # Controller引脚由GPIO独立配置，不在SPI Driver里操作其他IP。
        for gpio, function in support.dut.pins:
            support.gpio.configure_signal(gpio, function, master.instance_id)

        # Target的实例和引脚同样来自连接文件。
        for gpio, function in support.ref.pins:
            support.gpio.configure_signal(gpio, function, slave.instance_id)

        # 路由：通道0/1接收，通道2先装Target，通道3发送Controller数据。
        for interface, request in zip(
            interfaces, (rx_request_a, rx_request_b, tx_request_b, tx_request_a), strict=True
        ):
            sysctrl.configure_route(DmaRequestRoute(dma.instance_id, interface, request))
        tx_a = resource_driver.create(count * access_bits // 8)
        tx_b = resource_driver.create(count * access_bits // 8)
        rx_a = resource_driver.create(count * access_bits // 8)
        rx_b = resource_driver.create(count * access_bits // 8)
        master.configure(basic_config(support.dut, mode=SpiClockMode.MODE1, bits=8))
        slave.configure(
            basic_config(support.ref, role=SpiRole.TARGET, mode=SpiClockMode.MODE1, bits=8)
        )
        master.enable_set(True)
        slave.enable_set(True)
        master.dma_configure(True, True, 0, 0)
        slave.dma_configure(True, True, 0, 0)
        dma.controller_enable()
        configurations = (
            dma_config(
                0, interfaces[0], address_a, rx_a, count, receive=True, access_bits=access_bits
            ),
            dma_config(
                1, interfaces[1], address_b, rx_b, count, receive=True, access_bits=access_bits
            ),
            dma_config(
                2, interfaces[2], address_b, tx_b, count, receive=False, access_bits=access_bits
            ),
            dma_config(
                3, interfaces[3], address_a, tx_a, count, receive=False, access_bits=access_bits
            ),
        )

        # 每轮只换数据和重Arm DMA，不重置SPI，才能暴露串轮或残留状态。
        for round_index in range(rounds):
            # 输入：按轮号变化；接收缓冲先填不同值，禁止上轮结果冒充本轮搬运。
            sent = tuple(value ^ round_index for value in pattern(count, 8))
            reply = tuple(value ^ round_index for value in pattern(count, 8, inverse=True))
            resource_driver.write(tx_a, pack_frames(sent, access_bits))
            resource_driver.write(tx_b, pack_frames(reply, access_bits))
            resource_driver.write(rx_a, bytes([0xCD]) * rx_a.size)
            resource_driver.write(rx_b, bytes([0xCD]) * rx_b.size)
            record_property("round", round_index + 1)

            # 重Arm：清上一轮完成位、配置、启动；执行顺序保持RX/RX/Target TX/Controller TX。
            for configuration in configurations:
                dma.interrupt_pending_clear(
                    configuration.channel, DmaIrqEvent.TRANSFER_DONE | DmaIrqEvent.ERROR
                )
                dma.configure(configuration)
                dma.start(configuration.channel)
            slave.wait_tx_level(1, timeout_s=TIMEOUT_S)
            master.cs_set(True)
            states = dma.wait_channels_free((0, 1, 2, 3), timeout_s=TIMEOUT_S)
            master.cs_set(False)

            # 观测：目的区、通道事件和SPI原始状态在断言之前保存，失败轮次不重试。
            actual_a = unpack_frames(resource_driver.read(rx_a), access_bits)
            actual_b = unpack_frames(resource_driver.read(rx_b), access_bits)
            flags = [int(states[channel].interrupt_events) for channel in (0, 1, 2, 3)]
            status_a, status_b = master.error_status_read(), slave.error_status_read()
            fifo_a, fifo_b = master.snapshot_get(), slave.snapshot_get()
            history.append(
                {
                    "round": round_index + 1,
                    "expected_a": list(reply),
                    "expected_b": list(sent),
                    "rx_a": list(actual_a),
                    "rx_b": list(actual_b),
                    "dma": flags,
                    "status_a": int(status_a.flags),
                    "status_b": int(status_b.flags),
                }
            )
            record_property("rounds", history)
            record_observation(
                record_property, key="dma", value=flags, source="dut", endpoint="DMA.CHANNEL.EVENTS"
            )
            record_observation(
                record_property,
                key="data",
                value=[list(actual_a), list(actual_b)],
                source="dut",
                endpoint="DMA.MEMORY.RX",
            )
            record_observation(
                record_property,
                key="status",
                value=[int(status_a.flags), int(status_b.flags)],
                source="dut",
                endpoint="SPI.STATUS",
            )
            assert actual_a == reply and actual_b == sent
            assert all(
                flag & DmaIrqEvent.TRANSFER_DONE and not flag & DmaIrqEvent.ERROR for flag in flags
            )
            assert not (status_a.flags | status_b.flags) & (
                SpiStatusFlag.BUSY | SpiStatusFlag.TARGET_TX_ERROR | SpiStatusFlag.COLLISION
            )
            assert fifo_a.rx_level == fifo_a.tx_level == fifo_b.rx_level == fifo_b.tx_level == 0
