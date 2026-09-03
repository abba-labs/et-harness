# IPCM正式硬件Case，按P等级分类。
# 职责：显式配置、激励、取得双核硬件事实并断言。
# 边界：只调用公开Driver；不拼Wire、不访问寄存器、不硬编码芯片拓扑。
# 依赖：IPCM/CRG/Resource Driver、统一Deadline和Canonical Evidence。

import pytest

from ...core.deadline import OperationDeadline
from ...drivers.crg import CrgPeripheral
from ...drivers.ipcm.models import (
    IpcmAckMode,
    IpcmConfig,
    IpcmEventStage,
    IpcmLinkMode,
)
from ...scheduling.run_context import record_observation, require_evidence
from ..case_cleanup import case_cleanup_scope
from .ipcm_helpers import endpoint_mask, event_matches, pattern

pytestmark = [pytest.mark.hardware, pytest.mark.ip("ipcm")]


# 只返回直接恢复动作；Case最外层现有聚合器执行并保留主失败和清理失败。
def cleanup_actions(support, resource_driver):

    return (
        (
            "IPCM Peer cancel",
            lambda: support.local.peer_cancel(expected_identity=support.peer_identity),
        ),
        ("IPCM local Service reset", support.local.state_reset),
        (
            "IPCM hardware reset",
            lambda: support.crg.reset(CrgPeripheral.IPCM, instance=support.local.instance_id),
        ),
        ("Resource pool reset", resource_driver.reset),
    )


# =============================================================================
# 容量与基本Manual ACK
# =============================================================================


# 测试 Feature：
# IPCM容量、Source/Destination配置与Mailbox释放。
#
# 测试方法：
# 1. 复位IP与资源，读取CFG容量并与YAML逐项比较。
# 2. 配置一个Mailbox，读回路由、ACK/Link和IRQ Enable，再释放并检查空闲状态。
#
# 通过条件：
# 1. 三个容量一致，所有配置准确读回，释放后配置与两端Pending均为空。
def test_ipcm_p0_001_capability_and_release(ipcm_support, resource_driver, record_property):

    # 准备：角色来自Capability和Execution Mapping，不绑定芯片实例或IRQ编号。
    support = ipcm_support
    local, peer = support.local, support.peer
    source, destination = support.local_endpoint, support.peer_endpoint
    require_evidence(record_property, "dut", "peer")

    # 隔离：先停止两核Service，再复位本IP和整池资源；所有配置必须在此之后。
    local.peer_cancel(expected_identity=support.peer_identity)
    local.state_reset()
    support.crg.reset(CrgPeripheral.IPCM, instance=local.instance_id)
    peer.state_reset()
    resource_driver.reset()

    deadline = OperationDeadline.start(5.0, label="IPCM_P0_001")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 观测：读实际CFG字段，不能用本地配置缓存代替硬件容量。
        caps = local.capabilities_get(timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="actual_mailbox_count",
            value=caps.mailbox_count,
            source="dut",
            endpoint="CAPABILITY.MAILBOX_COUNT",
        )
        record_observation(
            record_property,
            key="actual_channel_count",
            value=caps.channel_count,
            source="dut",
            endpoint="CAPABILITY.CHANNEL_COUNT",
        )
        record_observation(
            record_property,
            key="actual_data_word_count",
            value=caps.data_word_count,
            source="dut",
            endpoint="CAPABILITY.DATA_WORD_COUNT",
        )

        assert (
            caps.mailbox_count,
            caps.channel_count,
            caps.data_word_count,
            caps.mailbox_payload_bytes,
        ) == (
            support.mailbox_count,
            support.channel_count,
            support.data_word_count,
            support.capacity,
        )

        # 配置：MANUAL/SINGLE，各角色使用不同逻辑Endpoint，随后逐字段读取真实配置。
        config = IpcmConfig(
            0,
            1,
            source,
            frozenset((destination,)),
            frozenset((source, destination)),
            IpcmAckMode.MANUAL,
            IpcmLinkMode.SINGLE,
        )
        local.configure(config, timeout_s=deadline.remaining_s())
        configured = local.mailbox_snapshot_get(0, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="configured_source_endpoints",
            value=endpoint_mask(configured.source_endpoints),
            source="dut",
            endpoint="MAILBOX.SOURCE_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="configured_destination_endpoints",
            value=endpoint_mask(configured.destination_endpoints),
            source="dut",
            endpoint="MAILBOX.DESTINATION_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="configured_irq_endpoints",
            value=endpoint_mask(configured.irq_enabled_endpoints),
            source="dut",
            endpoint="MAILBOX.IRQ_ENABLED_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="configured_ack_mode",
            value=configured.ack_mode.name,
            source="dut",
            endpoint="MAILBOX.ACK_MODE",
        )
        record_observation(
            record_property,
            key="configured_link_mode",
            value=configured.link_mode.name,
            source="dut",
            endpoint="MAILBOX.LINK_MODE",
        )

        assert configured.source_endpoints == frozenset((source,))
        assert configured.destination_endpoints == config.destination_endpoints
        assert configured.irq_enabled_endpoints == config.irq_enabled_endpoints
        assert configured.ack_mode is config.ack_mode and configured.link_mode is config.link_mode

        # 释放：只执行Mailbox release，不能通过整IP复位伪造释放成功。
        local.mailbox_release(0, 1, timeout_s=deadline.remaining_s())
        released = local.mailbox_snapshot_get(0, timeout_s=deadline.remaining_s())
        pending = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
        peer_pending = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="released_source_endpoints",
            value=endpoint_mask(released.source_endpoints),
            source="dut",
            endpoint="MAILBOX.SOURCE_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="released_destination_endpoints",
            value=endpoint_mask(released.destination_endpoints),
            source="dut",
            endpoint="MAILBOX.DESTINATION_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="released_irq_endpoints",
            value=endpoint_mask(released.irq_enabled_endpoints),
            source="dut",
            endpoint="MAILBOX.IRQ_ENABLED_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="released_raw_pending",
            value=pending.raw_pending,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="released_masked_pending",
            value=pending.masked_pending,
            source="dut",
            endpoint="CHANNEL.MASKED_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="peer_released_raw",
            value=peer_pending.raw_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )

        assert not (
            released.source_endpoints
            or released.destination_endpoints
            or released.irq_enabled_endpoints
        )
        assert (
            pending.raw_pending
            == pending.masked_pending
            == peer_pending.raw_pending
            == peer_pending.masked_pending
            == 0
        )


# 测试 Feature：
# 双Core变长Payload、Destination IRQ与原Payload Manual ACK。
#
# 测试方法：
# 1. 按容量参数选择长度，两端分别武装消息与ACK采样。
# 2. 本核写入并发送，Peer确认消息后由PC显式发ACK，本核取ACK后清中断。
#
# 通过条件：
# 1. 两端Payload逐字节一致，Raw/Masked只含当前Mailbox且每端回调一次。
# 2. 清除后两端Pending均为0。
@pytest.mark.parametrize(
    "length_kind", ("length_1", "length_3", "length_4", "length_max_minus_1", "length_max")
)
def test_ipcm_p0_002_manual_ack_payload(
    ipcm_support, resource_driver, record_property, length_kind
):

    # 准备：角色来自Capability和Execution Mapping，不绑定芯片实例或IRQ编号。
    support = ipcm_support
    local, peer = support.local, support.peer
    source, destination = support.local_endpoint, support.peer_endpoint
    require_evidence(record_property, "dut", "peer")
    support.require("manual_ack", "irq_delivery")

    # 隔离：先停止两核Service，再复位本IP和整池资源；所有配置必须在此之后。
    local.peer_cancel(expected_identity=support.peer_identity)
    local.state_reset()
    support.crg.reset(CrgPeripheral.IPCM, instance=local.instance_id)
    peer.state_reset()
    resource_driver.reset()

    length = {
        "length_1": 1,
        "length_3": 3,
        "length_4": 4,
        "length_max_minus_1": support.capacity - 1,
        "length_max": support.capacity,
    }[length_kind]
    if not 0 < length <= support.capacity:
        raise ValueError("IPCM capability cannot execute the declared length matrix")
    payload = pattern(length, 0x11)
    deadline = OperationDeadline.start(10.0, label="IPCM_P0_002")

    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 配置：两端ISR只保存一次事件，不在固件中自动ACK。
        local.configure(
            IpcmConfig(
                0,
                1,
                source,
                frozenset((destination,)),
                frozenset((source, destination)),
                IpcmAckMode.MANUAL,
                IpcmLinkMode.SINGLE,
            ),
            timeout_s=deadline.remaining_s(),
        )
        peer.capture_arm(
            0,
            destination,
            0,
            length,
            irq=True,
            stage=IpcmEventStage.MESSAGE,
            timeout_s=deadline.remaining_s(),
        )
        local.capture_arm(
            0,
            source,
            0,
            length,
            irq=True,
            stage=IpcmEventStage.ACK,
            timeout_s=deadline.remaining_s(),
        )

        # 激励：消息实际经过IPCM Data与SEND；Peer控制通道不替代被测消息。
        local.payload_write(0, 1, payload, timeout_s=deadline.remaining_s())
        local.message_send(0, timeout_s=deadline.remaining_s())
        message = peer.capture_wait(0, timeout_s=deadline.remaining_s())
        record_property("payload_length", length)
        record_observation(
            record_property,
            key="destination_raw_pending",
            value=message.raw_status,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="destination_masked_pending",
            value=message.masked_status,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.MASKED_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="received_payload",
            value=message.payload,
            source="peer",
            device_id="ipcm_peer",
            endpoint="MESSAGE.RECEIVED_PAYLOAD",
        )
        record_property("request_data_match", message.payload == payload)

        assert event_matches(message, payload, 0, destination, irq=True)

        # 应答：PC明确要求Peer发送原数据ACK，再读取Source的清除前快照。
        peer.ack_send(0, timeout_s=deadline.remaining_s())
        ack = local.capture_wait(0, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="source_raw_pending",
            value=ack.raw_status,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="source_masked_pending",
            value=ack.masked_status,
            source="dut",
            endpoint="CHANNEL.MASKED_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="ack_payload",
            value=ack.payload,
            source="dut",
            endpoint="ACK.RECEIVED_PAYLOAD",
        )
        ack_data_match = ack.payload == payload
        record_property("ack_data_match", ack_data_match)
        record_property("message_callback_count", message.callback_count)
        record_property("ack_callback_count", ack.callback_count)

        assert ack_data_match
        assert event_matches(ack, payload, 0, source, irq=True)

        # 终态：先清ACK再取即时Pending，不能用锁存快照冒充清除后状态。
        local.interrupt_clear(0, timeout_s=deadline.remaining_s())
        source_final = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
        destination_final = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="final_source_raw",
            value=source_final.raw_pending,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="final_destination_raw",
            value=destination_final.raw_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )

        assert (
            source_final.raw_pending
            == source_final.masked_pending
            == destination_final.raw_pending
            == destination_final.masked_pending
            == 0
        )
