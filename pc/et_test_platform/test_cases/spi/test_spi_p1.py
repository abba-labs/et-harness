# SPI P1外部数据、FIFO和错误路径。
# 职责：从连接文件选择双SPI，以明确的配置、刺激和硬件读回验证Feature。
# 边界：GPIO通过独立Driver配置，SPI不承担其他IP初始化。
# 依赖：本IP数据辅助、SPI/GPIO/CRG/Resource Driver和结果记录接口。

import time
from dataclasses import replace

import pytest

from ...drivers.crg import CrgPeripheral
from ...drivers.spi import SpiClockMode, SpiIrq, SpiRole, SpiStatusFlag, SpiTransferMode
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import TIMEOUT_S, basic_config, pattern

pytestmark = [pytest.mark.hardware, pytest.mark.ip("spi")]


# 测试 Feature：
# SPI MOSI→MISO真实PAD回接，四种模式及帧宽/分频边界。
#
# 测试方法：
# 1. 只在连接文件声明loopback角色且实物MOSI接MISO时执行，关闭内部Loopback。
# 2. 每个节点先复位SPI和资源，配置GPIO，再发送两组不同的8帧Pattern。
# 3. 读取完整RX、Loopback配置和BUSY/FIFO终态，逐帧对照独立输入。
#
# 通过条件：
# 1. 两组数据均精确匹配、内部Loopback为0，传输结束无残留帧且BUSY为0。
@pytest.mark.parametrize("mode", tuple(SpiClockMode))
@pytest.mark.parametrize("width_node", ("minimum", "byte", "maximum"))
@pytest.mark.parametrize("divider_node", ("minimum", "middle", "maximum"))
def test_spi_p1_001_external_loopback(
    spi_external_support, resource_driver, record_property, mode, width_node, divider_node
):

    # 准备：外部短接与双SPI对测是不同物理接线，Fixture只验证当前选择。
    support = spi_external_support
    endpoint, spi = support.dut, support.dut.spi
    limits = endpoint.limits
    bits = {
        "minimum": limits.frame_bits_min,
        "byte": max(limits.frame_bits_min, min(8, limits.frame_bits_max)),
        "maximum": limits.frame_bits_max,
    }[width_node]
    divider = {
        "minimum": limits.divider_min,
        "middle": ((limits.divider_min + limits.divider_max) // 4) * 2,
        "maximum": limits.divider_max,
    }[divider_node]
    support.crg.reset(CrgPeripheral.SPI, instance=spi.instance_id)
    resource_driver.reset()

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # GPIO独立配置；软件Loopback保持关闭，实际返回必须经过PAD。
        for gpio, function in endpoint.pins:
            support.gpio.configure_signal(gpio, function, spi.instance_id)
        spi.configure(basic_config(endpoint, mode=mode, bits=bits, divider=divider))
        spi.enable_set(True)
        loopback = spi.config_get().loopback
        record_observation(
            record_property,
            key="loopback",
            value=loopback,
            source="dut",
            endpoint="CONFIG.LOOPBACK",
        )
        assert not loopback
        nodes = []

        # 两组相反Pattern，完整数据与每组状态一起保存，不只保留最后一次观测。
        for inverse in (False, True):
            expected = pattern(8, bits, inverse=inverse)
            spi.write_frames(expected)
            spi.cs_set(True)
            actual = spi.read_exact(len(expected), timeout_s=TIMEOUT_S)
            spi.cs_set(False)
            status = spi.error_status_read()
            remaining = spi.snapshot_get().rx_level
            nodes.append(
                {
                    "expected": list(expected),
                    "actual": list(actual),
                    "status": int(status.flags),
                    "remaining": remaining,
                }
            )
            record_property("nodes", nodes)
            record_property("expected", list(expected))
            record_observation(
                record_property,
                key="rx",
                value=list(actual),
                source="dut",
                endpoint="TRANSFER.RX_DATA",
            )
            assert actual == expected and remaining == 0
            assert not status.flags & SpiStatusFlag.BUSY


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


# ==================== Target欠载与Controller启动水位 ====================


# 测试 Feature：
# SPI Target空TX错误状态、显式读清及补数据后的恢复。
#
# 测试方法：
# 1. 配置两端和GPIO，先完成一笔有预装返回帧的正常传输。
# 2. Target不补数据，Controller再发送一帧；停止时钟后连续两次读取错误状态。
# 3. Target补入新数据再收发，确认读清不是通过复位实现。
#
# 通过条件：
# 1. 错误首次为1、再次为0；补数据后返回帧正确且错误保持0。
def test_spi_p1_007_target_tx_error(spi_support, resource_driver, record_property):

    # 准备：连接文件决定物理两端，三次输入不同，避免旧FIFO数据伪装恢复。
    support = spi_support
    master, slave = support.dut.spi, support.ref.spi
    config = basic_config(support.dut)
    data = pattern(3, config.frame_bits)

    # 隔离：先复位参与SPI和资源，后续错误读清阶段禁止复位。
    support.crg.reset(CrgPeripheral.SPI, instance=master.instance_id)
    support.crg.reset(CrgPeripheral.SPI, instance=slave.instance_id)
    resource_driver.reset()

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 引脚：每个信号通过GPIO自己的命令链完成，不借SPI命令配置PAD。
        for endpoint in (support.dut, support.ref):
            # 当前实例只配置连接文件声明的四个信号。
            for gpio, function in endpoint.pins:
                support.gpio.configure_signal(gpio, function, endpoint.spi.instance_id)

        # 正常对照：先装Target再启动Controller，排空两端RX并读取无错误基线。
        slave.configure(basic_config(support.ref, role=SpiRole.TARGET, bits=config.frame_bits))
        master.configure(config)
        slave.enable_set(True)
        master.enable_set(True)
        slave.try_write_frame(data[0])
        master.try_write_frame(data[1])
        master.cs_set(True)
        normal = master.read_exact(1, timeout_s=TIMEOUT_S)
        slave.read_exact(1, timeout_s=TIMEOUT_S)
        master.cs_set(False)
        baseline = slave.error_status_read()
        record_property("normal_rx", list(normal))
        record_observation(
            record_property,
            key="baseline_status",
            value=int(baseline.flags),
            source="dut",
            endpoint="TARGET.STATUS",
        )
        assert normal == (data[0],)
        assert not baseline.flags & SpiStatusFlag.TARGET_TX_ERROR

        # 欠载：不给Target补数据，产生一帧新时钟；通用快照不会提前读取错误寄存器。
        master.try_write_frame(data[1])
        master.cs_set(True)
        master.read_exact(1, timeout_s=TIMEOUT_S)
        slave.read_exact(1, timeout_s=TIMEOUT_S)
        master.cs_set(False)
        first = slave.error_status_read()
        second = slave.error_status_read()
        record_observation(
            record_property,
            key="first",
            value=bool(first.flags & SpiStatusFlag.TARGET_TX_ERROR),
            source="dut",
            endpoint="TARGET.STATUS.TARGET_TX_ERROR",
        )
        record_observation(
            record_property,
            key="second",
            value=bool(second.flags & SpiStatusFlag.TARGET_TX_ERROR),
            source="dut",
            endpoint="TARGET.STATUS.TARGET_TX_ERROR",
        )

        # 恢复：不复位、不重新配置，只补一帧新返回数据并正常传输。
        slave.try_write_frame(data[2])
        master.try_write_frame(data[0])
        master.cs_set(True)
        recovery = master.read_exact(1, timeout_s=TIMEOUT_S)
        slave.read_exact(1, timeout_s=TIMEOUT_S)
        master.cs_set(False)
        recovered = slave.error_status_read()
        record_observation(
            record_property,
            key="rx",
            value=list(recovery),
            source="dut",
            endpoint="CONTROLLER.TRANSFER.RX_DATA",
        )
        assert first.flags & SpiStatusFlag.TARGET_TX_ERROR
        assert not second.flags & SpiStatusFlag.TARGET_TX_ERROR
        assert recovery == (data[2],) and not recovered.flags & SpiStatusFlag.TARGET_TX_ERROR


# 测试 Feature：
# SPI Controller的TX启动阈值，FIFO Level必须大于阈值才产生传输。
#
# 测试方法：
# 1. 每个合法T复位并配置两端；Target预装T+1帧返回数据。
# 2. Controller选择CS并装T帧，100ms观察窗口后Target RX仍为0。
# 3. 再装一帧越过阈值，接收全部T+1帧并逐帧比较。
#
# 通过条件：
# 1. 全部T在不足阈值时无RX，达到T+1后双方收到正确帧数和数据。
def test_spi_p1_008_start_threshold(spi_support, resource_driver, record_property):

    # 准备：阈值上限取两端FIFO较小容量，全部整数节点逐个执行。
    support = spi_support
    master, slave = support.dut.spi, support.ref.spi
    depth = min(support.dut.limits.fifo_depth, support.ref.limits.fifo_depth)
    config = replace(basic_config(support.dut), transfer_mode=SpiTransferMode.TX_ONLY)
    nodes = []

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 水位矩阵：同一Case覆盖0至D-1；每轮单独复位，不继承上一轮FIFO。
        for threshold in range(depth):
            # 隔离：所有配置之前复位两端SPI和整池资源。
            support.crg.reset(CrgPeripheral.SPI, instance=master.instance_id)
            support.crg.reset(CrgPeripheral.SPI, instance=slave.instance_id)
            resource_driver.reset()
            sent = pattern(threshold + 1, config.frame_bits)
            reply = pattern(threshold + 1, config.frame_bits, inverse=True)

            # GPIO：引脚选择只来自连接文件，配置在产生时钟之前完成。
            for gpio, function in support.dut.pins:
                support.gpio.configure_signal(gpio, function, master.instance_id)

            # Target侧也在启动前配置完成，避免复制第二层循环隐藏两个角色。
            for gpio, function in support.ref.pins:
                support.gpio.configure_signal(gpio, function, slave.instance_id)

            # 配置：Target先准备全部返回，Controller只写T帧并选CS。
            slave.configure(basic_config(support.ref, role=SpiRole.TARGET, bits=config.frame_bits))
            master.configure(config)
            slave.enable_set(True)
            slave.write_frames(reply)
            master.fifo_thresholds_set(0, 0, threshold)
            master.enable_set(True)
            master.write_frames(sent[:-1])
            master.cs_set(True)

            # 负向窗口：100ms用于证明不启动，不用固定延时替代后续完成等待。
            time.sleep(0.1)
            below = slave.snapshot_get().rx_level
            snapshot = master.snapshot_get()
            configured = snapshot.start_threshold
            record_observation(
                record_property,
                key="before",
                value=[snapshot.tx_level, below],
                source="dut",
                endpoint="TARGET.FIFO.RX_LEVEL",
            )
            record_observation(
                record_property,
                key="threshold",
                value=configured,
                source="dut",
                endpoint="FIFO.START_THRESHOLD",
            )
            assert below == 0 and snapshot.tx_level == threshold and configured == threshold

            # 越界：补第T+1帧，由硬件阈值启动，等待真实接收完成。
            master.try_write_frame(sent[-1])
            target_rx = slave.read_exact(threshold + 1, timeout_s=TIMEOUT_S)
            master.cs_set(False)
            final = master.snapshot_get()
            status = master.error_status_read()
            nodes.append(
                {
                    "threshold": threshold,
                    "target_rx": list(target_rx),
                    "status": int(status.flags),
                    "tx_level": final.tx_level,
                }
            )
            record_property("nodes", nodes)
            record_observation(
                record_property,
                key="rx",
                value=list(target_rx),
                source="dut",
                endpoint="TARGET.TRANSFER.RX_DATA",
            )
            assert target_rx == sent and final.tx_level == 0
            assert not status.flags & SpiStatusFlag.BUSY


# ==================== FIFO容量与独立阈值 ====================


# 测试 Feature：
# SPI TX/RX FIFO容量、Level变化、独立阈值读回及双FIFO复位。
#
# 测试方法：
# 1. 复位SPI和资源后，不选择CS逐帧填满TX并保存每一步Level。
# 2. 读回不同的TX/RX/启动阈值，通过内部回环填满RX，再逐帧排空。
# 3. 同时形成TX/RX非空后复位FIFO，检查两个Level清零。
#
# 通过条件：
# 1. 容量、满空标志、每一步Level和三个阈值均精确匹配，双FIFO一起复位。
@pytest.mark.parametrize("threshold_node", ("zero", "middle", "maximum"))
def test_spi_p1_004_fifo_capacity(spi_support, resource_driver, record_property, threshold_node):

    # 准备：容量取运行时范围，三个阈值取不同值，防止读错字段却碰巧相等。
    support, spi = spi_support, spi_support.dut.spi
    depth = support.dut.limits.fifo_depth
    threshold = {"zero": 0, "middle": depth // 2, "maximum": depth - 1}[threshold_node]
    rx_threshold, start_threshold = (threshold + 1) % depth, (threshold + 2) % depth
    config = basic_config(support.dut, loopback=True)
    frames = pattern(depth, config.frame_bits)

    # 隔离：首先复位参与SPI，再复位资源池，后面的fifo_reset才是被测动作。
    support.crg.reset(CrgPeripheral.SPI, instance=spi.instance_id)
    resource_driver.reset()

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 静止TX：未选择CS时逐帧写入，Level不得因外部时钟自行减少。
        spi.configure(config)
        spi.enable_set(True)
        tx_levels = [spi.snapshot_get().tx_level]

        # 填充：每次只写一帧并立刻读取占用数量，逐步证明全部容量。
        for frame in frames:
            accepted = spi.try_write_frame(frame)
            tx_levels.append(spi.snapshot_get().tx_level)
            record_observation(
                record_property,
                key="tx_level",
                value=tx_levels,
                source="dut",
                endpoint="FIFO.TX_LEVEL",
            )
            assert accepted and tx_levels[-1] == len(tx_levels) - 1

        # 满状态：在任何FIFO复位前读取TX满标志，避免终态代替容量证据。
        full_tx = spi.error_status_read()
        record_observation(
            record_property,
            key="full_tx_status",
            value=int(full_tx.flags),
            source="dut",
            endpoint="STATUS.TX_FULL",
        )
        assert not full_tx.flags & SpiStatusFlag.TX_NOT_FULL
        spi.fifo_thresholds_set(threshold, rx_threshold, start_threshold)
        thresholds = spi.snapshot_get()
        record_observation(
            record_property,
            key="tx_threshold",
            value=thresholds.tx_threshold,
            source="dut",
            endpoint="FIFO.TX_THRESHOLD",
        )
        record_observation(
            record_property,
            key="rx_threshold",
            value=thresholds.rx_threshold,
            source="dut",
            endpoint="FIFO.RX_THRESHOLD",
        )
        record_observation(
            record_property,
            key="start_threshold",
            value=thresholds.start_threshold,
            source="dut",
            endpoint="FIFO.START_THRESHOLD",
        )
        assert (thresholds.tx_threshold, thresholds.rx_threshold, thresholds.start_threshold) == (
            threshold,
            rx_threshold,
            start_threshold,
        )

        # RX容量：启动已填满的TX，不消费接收数据，等RX真实达到容量。
        spi.cs_set(True)
        spi.wait_rx_level(depth, timeout_s=TIMEOUT_S)
        full_rx = spi.error_status_read()
        rx_levels = [spi.snapshot_get().rx_level]
        assert full_rx.flags & SpiStatusFlag.RX_FULL

        # 排空：每次读取都比对独立输入，Level必须精确减一。
        for index, expected in enumerate(frames):
            actual = spi.try_read_frame()
            rx_levels.append(spi.snapshot_get().rx_level)
            record_observation(
                record_property,
                key="rx_level",
                value=rx_levels,
                source="dut",
                endpoint="FIFO.RX_LEVEL",
            )
            assert actual == expected and rx_levels[-1] == depth - index - 1

        # 复位刺激：RX中保留一帧，再取消CS并在TX装一帧，验证两个FIFO同时清空。
        spi.fifo_thresholds_set(0, 0, 0)
        spi.try_write_frame(frames[0])
        spi.wait_rx_level(1, timeout_s=TIMEOUT_S)
        spi.cs_set(False)
        spi.try_write_frame(frames[0])
        before = spi.snapshot_get()
        spi.fifo_reset()
        after = spi.snapshot_get()
        record_property("reset_before", {"tx": before.tx_level, "rx": before.rx_level})
        record_observation(
            record_property,
            key="reset_tx",
            value=after.tx_level,
            source="dut",
            endpoint="FIFO.TX_LEVEL",
        )
        record_observation(
            record_property,
            key="reset_rx",
            value=after.rx_level,
            source="dut",
            endpoint="FIFO.RX_LEVEL",
        )
        assert before.tx_level == before.rx_level == 1
        assert after.tx_level == after.rx_level == 0


# ==================== FIFO中断的触发、投递和解除 ====================


# 测试 Feature：
# SPI TXE、TXO、RXU、RXO、RXF源的Raw、Mask、NVIC投递和正确清除。
#
# 测试方法：
# 1. 每个源、阈值节点复位后保持Mask，按容量或水位产生最小真实刺激。
# 2. 先检查Raw与Mask后Status，再Unmask并绑定IRQ，读取ISR锁存。
# 3. 电平源移除FIFO条件，锁存源停止刺激后清除，重新开放验证不再投递。
#
# 通过条件：
# 1. Mask无投递、Unmask有对应IRQ；清除后Raw为0且事件计数不增加。
@pytest.mark.parametrize(
    "source",
    (SpiIrq.TX_EMPTY, SpiIrq.TX_OVERFLOW, SpiIrq.RX_UNDERFLOW, SpiIrq.RX_OVERFLOW, SpiIrq.RX_FULL),
)
@pytest.mark.parametrize("threshold_node", ("zero", "middle", "maximum"))
def test_spi_p1_005_fifo_irq(spi_support, resource_driver, record_property, source, threshold_node):

    # 准备：阈值域覆盖0、中间值、容量减一；每个参数execution重新建立基线。
    support, spi = spi_support, spi_support.dut.spi
    depth = support.dut.limits.fifo_depth
    threshold = {"zero": 0, "middle": depth // 2, "maximum": depth - 1}[threshold_node]
    config = basic_config(support.dut, loopback=True)

    # 隔离：停止本IP旧采集后复位硬件，再复位整池资源，不依赖上一Case的Mask。
    spi.irq_capture_stop()
    support.crg.reset(CrgPeripheral.SPI, instance=spi.instance_id)
    resource_driver.reset()

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_driver)):
        # 配置：全部源保持屏蔽，TX/RX阈值相同，启动阈值为0，不让ISR排空FIFO。
        spi.configure(config)
        spi.enable_set(True)
        spi.fifo_thresholds_set(threshold, threshold, 0)
        spi.irq_mask_set(SpiIrq.ALL, False)
        spi.irq_event_reset()

        # 刺激：每个分支只制造自己的目标条件，错误访问使用明确的测试Driver接口。
        if source == SpiIrq.TX_EMPTY:
            spi.write_frames(pattern(threshold, config.frame_bits))
        elif source == SpiIrq.TX_OVERFLOW:
            spi.write_frames(pattern(depth, config.frame_bits))
            spi.test_fifo_write_once(1)
        elif source == SpiIrq.RX_UNDERFLOW:
            spi.test_fifo_read_once()
        else:
            receive_count = depth if source == SpiIrq.RX_OVERFLOW else threshold
            spi.write_frames(pattern(receive_count, config.frame_bits))
            spi.cs_set(True)
            spi.wait_rx_level(receive_count, timeout_s=TIMEOUT_S)
            if source == SpiIrq.RX_FULL:
                assert not spi.snapshot_get().irq_raw & source
            spi.try_write_frame(1)

        # Mask证据：等待硬件Raw出现，但有效Status和软件事件仍为0。
        masked = spi.wait_irq_raw(source, timeout_s=TIMEOUT_S)
        before_events = spi.irq_event_get().event_count
        record_observation(
            record_property, key="raw", value=int(masked.irq_raw), source="dut", endpoint="IRQ.RAW"
        )
        record_observation(
            record_property,
            key="masked_status",
            value=int(masked.irq_status),
            source="dut",
            endpoint="IRQ.STATUS",
        )
        record_property("before_events", before_events)
        assert not masked.irq_status & source and before_events == 0

        # 投递：先保存有效Status再绑定NVIC，ISR只锁存并屏蔽当前源，避免IRQ风暴。
        spi.irq_mask_set(source, True)
        status = spi.snapshot_get().irq_status
        spi.irq_capture_start(source)
        event = spi.irq_wait(timeout_s=TIMEOUT_S)
        record_observation(
            record_property, key="status", value=int(status), source="dut", endpoint="IRQ.STATUS"
        )
        record_property("isr_source", int(event.latched_events))
        record_property("events", event.event_count)
        assert status & source and event.latched_events & source
        assert event.event_count >= 1 and event.unexpected_count == event.fault_flags == 0

        # 解除：TXE补到T+1，RXF读到R，其余停止错误刺激后执行对应锁存源清除。
        if source == SpiIrq.TX_EMPTY:
            spi.try_write_frame(1)
        elif source == SpiIrq.RX_FULL:
            spi.try_read_frame()
        else:
            spi.irq_clear(source)
        cleared = spi.snapshot_get()
        spi.irq_mask_set(source, True)
        after_events = spi.irq_event_get().event_count
        record_observation(
            record_property,
            key="cleared_raw",
            value=int(cleared.irq_raw),
            source="dut",
            endpoint="IRQ.RAW",
        )
        assert not cleared.irq_raw & source
        assert after_events == event.event_count


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
