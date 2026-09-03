# IPCM正式硬件Case，按P等级分类。
# 职责：显式配置、激励、取得双核硬件事实并断言。
# 边界：只调用公开Driver；不拼Wire、不访问寄存器、不硬编码芯片拓扑。
# 依赖：IPCM/CRG/Resource Driver、统一Deadline和Canonical Evidence。

import pytest

from ...core.deadline import OperationDeadline
from ...drivers.crg import CrgPeripheral
from ...drivers.ipcm.models import (
    IpcmAckMode,
    IpcmCaptureState,
    IpcmConfig,
    IpcmEventStage,
    IpcmLinkMode,
)
from ...results.recorder import write_json_result
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
# ACK与事件投递
# =============================================================================


# 测试 Feature：
# Manual ACK更新Payload。
#
# 测试方法：
# 1. 发送Pattern A并锁存Peer实际接收值，随后通过Peer写入不同的Pattern B。
# 2. 显式发送ACK，保存Source ACK数据与IRQ状态，再清除两端Pending。
#
# 通过条件：
# 1. 请求等于A、ACK等于B，消息和ACK各回调一次，终态无Pending。
def test_ipcm_p1_001_ack_payload_update(ipcm_support, resource_driver, record_property):

    # 准备：角色来自Capability和Execution Mapping，不绑定芯片实例或IRQ编号。
    support = ipcm_support
    local, peer = support.local, support.peer
    source, destination = support.local_endpoint, support.peer_endpoint
    require_evidence(record_property, "dut", "peer")
    support.require("ack_payload_update", "manual_ack")

    # 隔离：先停止两核Service，再复位本IP和整池资源；所有配置必须在此之后。
    local.peer_cancel(expected_identity=support.peer_identity)
    local.state_reset()
    support.crg.reset(CrgPeripheral.IPCM, instance=local.instance_id)
    peer.state_reset()
    resource_driver.reset()

    length = min(7, support.capacity)
    payload, replacement = pattern(length, 0x21), pattern(length, 0xA1)
    deadline = OperationDeadline.start(5.0, label="IPCM_P1_001")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 配置：消息和ACK分别交给对应Core采样，采用MANUAL模式。
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

        # 请求：先收到A再允许覆盖，避免ACK更新掩盖原请求数据。
        local.payload_write(0, 1, payload, timeout_s=deadline.remaining_s())
        local.message_send(0, timeout_s=deadline.remaining_s())
        message = peer.capture_wait(0, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="request_payload",
            value=message.payload,
            source="peer",
            device_id="ipcm_peer",
            endpoint="MESSAGE.RECEIVED_PAYLOAD",
        )

        assert event_matches(message, payload, 0, destination, irq=True)

        # ACK更新：Peer只写入B，PC随后单独下发ACK动作。
        peer.payload_write(0, 1, replacement, timeout_s=deadline.remaining_s())
        peer.ack_send(0, timeout_s=deadline.remaining_s())
        ack = local.capture_wait(0, timeout_s=deadline.remaining_s())
        record_property("expected_ack_payload", replacement)
        record_observation(
            record_property,
            key="actual_ack_payload",
            value=ack.payload,
            source="dut",
            endpoint="ACK.RECEIVED_PAYLOAD",
        )
        record_observation(
            record_property,
            key="ack_raw_pending",
            value=ack.raw_status,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="ack_masked_pending",
            value=ack.masked_status,
            source="dut",
            endpoint="CHANNEL.MASKED_PENDING_MAILBOXES",
        )
        record_property("ack_callback_delta", ack.callback_count)

        assert event_matches(ack, replacement, 0, source, irq=True)
        assert ack.payload != message.payload

        # 清除：检查实际终态，下一Case不能继承当前ACK。
        local.interrupt_clear(0, timeout_s=deadline.remaining_s())
        final = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
        peer_final = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        record_property(
            "final_pending",
            [
                final.raw_pending,
                final.masked_pending,
                peer_final.raw_pending,
                peer_final.masked_pending,
            ],
        )
        assert (
            final.raw_pending
            == final.masked_pending
            == peer_final.raw_pending
            == peer_final.masked_pending
            == 0
        )


# 测试 Feature：
# AUTO ACK：清中断不ACK，释放Destination才ACK。
#
# 测试方法：
# 1. 两个独立参数分别执行clear_only与release，不混用动作。
# 2. 前者完整观察100ms无ACK；后者等待原Payload ACK，再核对Destination变化。
#
# 通过条件：
# 1. clear_only保留Destination且无ACK；release清Destination且只产生一次原数据ACK。
@pytest.mark.parametrize("responder_action", ("clear_only", "release"))
def test_ipcm_p1_002_auto_ack_trigger(
    ipcm_support, resource_driver, record_property, responder_action
):

    # 准备：角色来自Capability和Execution Mapping，不绑定芯片实例或IRQ编号。
    support = ipcm_support
    local, peer = support.local, support.peer
    source, destination = support.local_endpoint, support.peer_endpoint
    require_evidence(record_property, "dut", "peer")
    support.require("auto_ack")

    # 隔离：先停止两核Service，再复位本IP和整池资源；所有配置必须在此之后。
    local.peer_cancel(expected_identity=support.peer_identity)
    local.state_reset()
    support.crg.reset(CrgPeripheral.IPCM, instance=local.instance_id)
    peer.state_reset()
    resource_driver.reset()

    length = min(7, support.capacity)
    payload = pattern(length, 0x31 if responder_action == "clear_only" else 0xB1)
    deadline = OperationDeadline.start(8.0, label="IPCM_P1_002")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 配置：AUTO模式、同一个Destination，两个参数只改变接收后的唯一动作。
        local.configure(
            IpcmConfig(
                0,
                1,
                source,
                frozenset((destination,)),
                frozenset((source, destination)),
                IpcmAckMode.AUTO,
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
        local.payload_write(0, 1, payload, timeout_s=deadline.remaining_s())
        local.message_send(0, timeout_s=deadline.remaining_s())
        message = peer.capture_wait(0, timeout_s=deadline.remaining_s())
        before = peer.mailbox_snapshot_get(0, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="received_payload",
            value=message.payload,
            source="peer",
            device_id="ipcm_peer",
            endpoint="MESSAGE.RECEIVED_PAYLOAD",
        )
        record_observation(
            record_property,
            key="destination_before_action",
            value=endpoint_mask(before.destination_endpoints),
            source="peer",
            device_id="ipcm_peer",
            endpoint="MAILBOX.DESTINATION_ENDPOINTS",
        )
        record_property("responder_action", responder_action)

        assert event_matches(message, payload, 0, destination, irq=True)

        # 激励：反向参数不补做release；通信超时仍为失败，不能解释为无ACK。
        if responder_action == "clear_only":
            peer.interrupt_clear(0, timeout_s=deadline.remaining_s())
            ack = local.capture_observe(0, window_s=0.1, timeout_s=deadline.remaining_s())
        else:
            peer.destination_release(0, destination, timeout_s=deadline.remaining_s())
            ack = local.capture_wait(0, timeout_s=deadline.remaining_s())

        # 观测：所有参数记录相同语义的动作后路由和Source事件，保留观测阶段。
        after = peer.mailbox_snapshot_get(0, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="destination_after_action",
            value=endpoint_mask(after.destination_endpoints),
            source="peer",
            device_id="ipcm_peer",
            endpoint="MAILBOX.DESTINATION_ENDPOINTS",
        )
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
        record_property("ack_callback_delta", ack.callback_count)

        if responder_action == "clear_only":
            instantaneous = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="window_final_raw",
                value=instantaneous.raw_pending,
                source="dut",
                endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
            )
            assert ack.state is IpcmCaptureState.WAITING
            assert (
                ack.raw_status
                == ack.masked_status
                == ack.callback_count
                == instantaneous.raw_pending
                == instantaneous.masked_pending
                == 0
            )
            assert (
                after.destination_endpoints
                == before.destination_endpoints
                == frozenset((destination,))
            )
        else:
            record_observation(
                record_property,
                key="ack_payload",
                value=ack.payload,
                source="dut",
                endpoint="ACK.RECEIVED_PAYLOAD",
            )
            assert event_matches(ack, payload, 0, source, irq=True)
            assert not after.destination_endpoints
            local.interrupt_clear(0, timeout_s=deadline.remaining_s())


# 测试 Feature：
# 同一消息的IRQ与Polling投递区别。
#
# 测试方法：
# 1. MANUAL模式按参数关闭或开启IRQ，消息采样后仅清中断、不ACK。
# 2. 读取清除前Raw/Masked、真实回调增量和清除后即时Pending。
#
# 通过条件：
# 1. Polling为Raw=目标位、Masked=0、回调0；IRQ为Raw/Masked=目标位、回调1；数据均一致。
@pytest.mark.parametrize("delivery_mode", ("polling", "irq"))
def test_ipcm_p1_003_delivery_mode(ipcm_support, resource_driver, record_property, delivery_mode):

    # 准备：角色来自Capability和Execution Mapping，不绑定芯片实例或IRQ编号。
    support = ipcm_support
    local, peer = support.local, support.peer
    source, destination = support.local_endpoint, support.peer_endpoint
    require_evidence(record_property, "dut", "peer")
    support.require("polling", "irq_delivery")

    # 隔离：先停止两核Service，再复位本IP和整池资源；所有配置必须在此之后。
    local.peer_cancel(expected_identity=support.peer_identity)
    local.state_reset()
    support.crg.reset(CrgPeripheral.IPCM, instance=local.instance_id)
    peer.state_reset()
    resource_driver.reset()

    irq = delivery_mode == "irq"
    length = min(7, support.capacity)
    payload = pattern(length, 0xC1 if irq else 0x41)
    deadline = OperationDeadline.start(8.0, label="IPCM_P1_003")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 配置：IRQ位集合与采样方式同步选择；不启用Source ACK采样。
        local.configure(
            IpcmConfig(
                0,
                1,
                source,
                frozenset((destination,)),
                frozenset((destination,)) if irq else frozenset(),
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
            irq=irq,
            stage=IpcmEventStage.MESSAGE,
            timeout_s=deadline.remaining_s(),
        )

        # 激励与观测：锁存真实消息事件，清除动作留在PC，不自动ACK。
        local.payload_write(0, 1, payload, timeout_s=deadline.remaining_s())
        local.message_send(0, timeout_s=deadline.remaining_s())
        message = peer.capture_wait(0, timeout_s=deadline.remaining_s())
        record_property("delivery_mode", delivery_mode)
        record_observation(
            record_property,
            key="event_raw_pending",
            value=message.raw_status,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="event_masked_pending",
            value=message.masked_status,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.MASKED_PENDING_MAILBOXES",
        )
        record_property("callback_delta", message.callback_count)
        record_property("payload_data_match", message.payload == payload)
        record_observation(
            record_property,
            key="received_payload",
            value=message.payload,
            source="peer",
            device_id="ipcm_peer",
            endpoint="MESSAGE.RECEIVED_PAYLOAD",
        )

        assert event_matches(message, payload, 0, destination, irq=irq)

        # 终态：清除后两个Pending字段都必须为0，锁存回调计数不能重复增长。
        peer.interrupt_clear(0, timeout_s=deadline.remaining_s())
        final = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        retained = peer.capture_get(0, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="final_raw",
            value=final.raw_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="final_masked",
            value=final.masked_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.MASKED_PENDING_MAILBOXES",
        )
        assert final.raw_pending == final.masked_pending == 0
        assert retained.callback_count == message.callback_count


# =============================================================================
# Mailbox复用与独立路由
# =============================================================================


# 测试 Feature：
# 全Mailbox寻址、释放和同一Mailbox复用。
#
# 测试方法：
# 1. 从Capability展开全部Mailbox，每项执行两轮不同Payload的Manual ACK。
# 2. 每轮释放后读取Source、Destination、IRQ Enable及两端Pending。
#
# 通过条件：
# 1. 两轮消息与ACK准确、事件各一次，释放配置及Pending均为空。
def test_ipcm_p1_004_all_mailbox_reuse(
    ipcm_support, resource_driver, record_property, et_artifact_dir, ipcm_mailbox
):

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

    if ipcm_mailbox is None or not 0 <= ipcm_mailbox < support.mailbox_count:
        raise ValueError("IPCM mailbox matrix requires a selected Bench capability")
    mailbox = ipcm_mailbox
    length = min(7, support.capacity)
    rounds = []
    deadline = OperationDeadline.start(20.0, label="IPCM_P1_004")
    record_property("mailbox_id", mailbox)
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 复用循环：只在execution开始整IP复位，第二轮必须依靠Mailbox释放后的真实状态。
        for round_index in range(2):
            payload = pattern(length, mailbox + round_index * 0x80)

            # 配置与武装：每轮重新声明路由，恢复被ISR暂停的IRQ投递。
            local.configure(
                IpcmConfig(
                    mailbox,
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
                mailbox,
                length,
                irq=True,
                stage=IpcmEventStage.MESSAGE,
                timeout_s=deadline.remaining_s(),
            )
            local.capture_arm(
                0,
                source,
                mailbox,
                length,
                irq=True,
                stage=IpcmEventStage.ACK,
                timeout_s=deadline.remaining_s(),
            )

            # 请求与ACK：PC看到Peer接收后再下发ACK，不在固件里组合流程。
            local.payload_write(mailbox, 1, payload, timeout_s=deadline.remaining_s())
            local.message_send(mailbox, timeout_s=deadline.remaining_s())
            message = peer.capture_wait(0, timeout_s=deadline.remaining_s())
            peer.ack_send(mailbox, timeout_s=deadline.remaining_s())
            ack = local.capture_wait(0, timeout_s=deadline.remaining_s())

            # 释放与观测：保存每轮完整证据到不同阶段，不覆盖首轮现场。
            local.interrupt_clear(mailbox, timeout_s=deadline.remaining_s())
            local.mailbox_release(mailbox, 1, timeout_s=deadline.remaining_s())
            released = local.mailbox_snapshot_get(mailbox, timeout_s=deadline.remaining_s())
            final = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
            peer_final = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
            data_match = message.payload == ack.payload == payload
            rounds.append(
                {
                    "round": round_index,
                    "message": message.payload,
                    "ack": ack.payload,
                    "message_raw": message.raw_status,
                    "ack_raw": ack.raw_status,
                    "message_count": message.callback_count,
                    "ack_count": ack.callback_count,
                    "released_source": endpoint_mask(released.source_endpoints),
                    "released_destination": endpoint_mask(released.destination_endpoints),
                    "released_irq": endpoint_mask(released.irq_enabled_endpoints),
                    "raw": final.raw_pending,
                    "peer_raw": peer_final.raw_pending,
                }
            )
            if round_index == 0:
                record_property("first_data_match", data_match)
            else:
                record_property("reuse_data_match", data_match)
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
                key="released_irq_enabled_endpoints",
                value=endpoint_mask(released.irq_enabled_endpoints),
                source="dut",
                endpoint="MAILBOX.IRQ_ENABLED_ENDPOINTS",
            )
            record_observation(
                record_property,
                key="released_raw_pending",
                value=final.raw_pending,
                source="dut",
                endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
            )
            record_observation(
                record_property,
                key="released_masked_pending",
                value=final.masked_pending,
                source="dut",
                endpoint="CHANNEL.MASKED_PENDING_MAILBOXES",
            )
            record_observation(
                record_property,
                key="peer_payload",
                value=message.payload,
                source="peer",
                device_id="ipcm_peer",
                endpoint="MESSAGE.RECEIVED_PAYLOAD",
            )

            write_json_result(et_artifact_dir / f"ipcm_reuse_round_{round_index}.json", rounds[-1])
            assert data_match
            assert event_matches(message, payload, mailbox, destination, irq=True)
            assert event_matches(ack, payload, mailbox, source, irq=True)
            assert not (
                released.source_endpoints
                or released.destination_endpoints
                or released.irq_enabled_endpoints
            )
            assert (
                final.raw_pending
                == final.masked_pending
                == peer_final.raw_pending
                == peer_final.masked_pending
                == 0
            )


# 测试 Feature：
# 双核双Mailbox双向消息与独立路由。
#
# 测试方法：
# 1. 配置正向和反向两个Mailbox，正向接收完成并清中断后才发送反向消息。
# 2. 两方向均只收消息、不ACK，分别保存真实路由、数据和事件。
#
# 通过条件：
# 1. 两方向Mailbox/Endpoint正确、Payload不串扰，各回调一次且最终无Pending。
def test_ipcm_p1_005_bidirectional_mailboxes(ipcm_support, resource_driver, record_property):

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

    assert support.mailbox_count >= 2
    length = min(7, support.capacity)
    forward_payload, reverse_payload = pattern(length, 0x51), pattern(length, 0xD1)
    deadline = OperationDeadline.start(8.0, label="IPCM_P1_005")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 配置：正向用Mailbox0，反向用另一个合法Mailbox1，交换Source/Destination。
        local.configure(
            IpcmConfig(
                0,
                1,
                source,
                frozenset((destination,)),
                frozenset((destination,)),
                IpcmAckMode.MANUAL,
                IpcmLinkMode.SINGLE,
            ),
            timeout_s=deadline.remaining_s(),
        )
        peer.configure(
            IpcmConfig(
                1,
                1,
                destination,
                frozenset((source,)),
                frozenset((source,)),
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
            1,
            length,
            irq=True,
            stage=IpcmEventStage.MESSAGE,
            timeout_s=deadline.remaining_s(),
        )

        # 正向：先读Peer实际数据及路由，再允许反向发送。
        local.payload_write(0, 1, forward_payload, timeout_s=deadline.remaining_s())
        local.message_send(0, timeout_s=deadline.remaining_s())
        forward = peer.capture_wait(0, timeout_s=deadline.remaining_s())
        forward_route = peer.mailbox_snapshot_get(0, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="forward_mailbox_id",
            value=forward.raw_status.bit_length() - 1,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.PENDING_MAILBOX_ID",
        )
        record_observation(
            record_property,
            key="forward_source_endpoints",
            value=endpoint_mask(forward_route.source_endpoints),
            source="peer",
            device_id="ipcm_peer",
            endpoint="MAILBOX.SOURCE_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="forward_destination_endpoints",
            value=endpoint_mask(forward_route.destination_endpoints),
            source="peer",
            device_id="ipcm_peer",
            endpoint="MAILBOX.DESTINATION_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="forward_payload",
            value=forward.payload,
            source="peer",
            device_id="ipcm_peer",
            endpoint="MESSAGE.RECEIVED_PAYLOAD",
        )
        record_property("forward_data_match", forward.payload == forward_payload)
        assert event_matches(forward, forward_payload, 0, destination, irq=True)
        assert forward_route.source_endpoints == frozenset(
            (source,)
        ) and forward_route.destination_endpoints == frozenset((destination,))
        peer.interrupt_clear(0, timeout_s=deadline.remaining_s())

        # 反向：由独立Peer执行写入和SEND，本核ISR接收第二个Mailbox。
        peer.payload_write(1, 1, reverse_payload, timeout_s=deadline.remaining_s())
        peer.message_send(1, timeout_s=deadline.remaining_s())
        reverse = local.capture_wait(0, timeout_s=deadline.remaining_s())
        reverse_route = local.mailbox_snapshot_get(1, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="reverse_mailbox_id",
            value=reverse.raw_status.bit_length() - 1,
            source="dut",
            endpoint="CHANNEL.PENDING_MAILBOX_ID",
        )
        record_observation(
            record_property,
            key="reverse_source_endpoints",
            value=endpoint_mask(reverse_route.source_endpoints),
            source="dut",
            endpoint="MAILBOX.SOURCE_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="reverse_destination_endpoints",
            value=endpoint_mask(reverse_route.destination_endpoints),
            source="dut",
            endpoint="MAILBOX.DESTINATION_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="reverse_payload",
            value=reverse.payload,
            source="dut",
            endpoint="MESSAGE.RECEIVED_PAYLOAD",
        )
        record_property("reverse_data_match", reverse.payload == reverse_payload)
        assert event_matches(reverse, reverse_payload, 1, source, irq=True)
        assert reverse_route.source_endpoints == frozenset(
            (destination,)
        ) and reverse_route.destination_endpoints == frozenset((source,))

        # 终态：两个方向都不能遗留事件，不能等待未请求的ACK。
        local.interrupt_clear(1, timeout_s=deadline.remaining_s())
        final = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
        peer_final = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        record_property(
            "final_pending",
            [
                final.raw_pending,
                final.masked_pending,
                peer_final.raw_pending,
                peer_final.masked_pending,
            ],
        )
        assert (
            final.raw_pending
            == final.masked_pending
            == peer_final.raw_pending
            == peer_final.masked_pending
            == 0
        )


# 测试 Feature：
# 两Mailbox同时Pending与独立清除。
#
# 测试方法：
# 1. 关闭IRQ后连续发送两条消息，Peer先读完整Raw位集合，再逐个读数据和清除。
# 2. 对比清除前、清第一位后、全清后的Raw/Masked。
#
# 通过条件：
# 1. Raw从两位变为仅第二位再变0；Masked始终0，两份数据各自正确。
def test_ipcm_p1_006_multiple_pending(ipcm_support, resource_driver, record_property):

    # 准备：角色来自Capability和Execution Mapping，不绑定芯片实例或IRQ编号。
    support = ipcm_support
    local, peer = support.local, support.peer
    source, destination = support.local_endpoint, support.peer_endpoint
    require_evidence(record_property, "dut", "peer")
    support.require("polling")

    # 隔离：先停止两核Service，再复位本IP和整池资源；所有配置必须在此之后。
    local.peer_cancel(expected_identity=support.peer_identity)
    local.state_reset()
    support.crg.reset(CrgPeripheral.IPCM, instance=local.instance_id)
    peer.state_reset()
    resource_driver.reset()

    assert support.mailbox_count >= 2
    length = min(7, support.capacity)
    payload_a, payload_b = pattern(length, 0x61), pattern(length, 0xE1)
    deadline = OperationDeadline.start(8.0, label="IPCM_P1_006")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 配置与激励：先全部SEND再交给Peer处理；不能让捕获回调提前清掉第一项。
        for mailbox, payload in ((0, payload_a), (1, payload_b)):
            local.configure(
                IpcmConfig(
                    mailbox,
                    1,
                    source,
                    frozenset((destination,)),
                    frozenset(),
                    IpcmAckMode.MANUAL,
                    IpcmLinkMode.SINGLE,
                ),
                timeout_s=deadline.remaining_s(),
            )
            local.payload_write(mailbox, 1, payload, timeout_s=deadline.remaining_s())
            local.message_send(mailbox, timeout_s=deadline.remaining_s())

        # 处理：完整位集合读取，清一项不应影响另一项。
        before = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        actual_a = peer.payload_read(0, length, timeout_s=deadline.remaining_s())
        peer.interrupt_clear(0, timeout_s=deadline.remaining_s())
        after_first = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        actual_b = peer.payload_read(1, length, timeout_s=deadline.remaining_s())
        peer.interrupt_clear(1, timeout_s=deadline.remaining_s())
        after_all = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="pending_before",
            value=before.raw_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="pending_after_first",
            value=after_first.raw_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="pending_after_all",
            value=after_all.raw_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="masked_pending",
            value=before.masked_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.MASKED_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="mailbox_a_payload",
            value=actual_a,
            source="peer",
            device_id="ipcm_peer",
            endpoint="MESSAGE.RECEIVED_PAYLOAD_A",
        )
        record_observation(
            record_property,
            key="mailbox_b_payload",
            value=actual_b,
            source="peer",
            device_id="ipcm_peer",
            endpoint="MESSAGE.RECEIVED_PAYLOAD_B",
        )

        record_property("payloads_match", actual_a == payload_a and actual_b == payload_b)
        assert (before.raw_pending, after_first.raw_pending, after_all.raw_pending) == (3, 2, 0)
        assert before.masked_pending == after_first.masked_pending == after_all.masked_pending == 0
        assert actual_a == payload_a and actual_b == payload_b


# 测试 Feature：
# Multi-destination独立投递和逐目标释放。
#
# 测试方法：
# 1. MANUAL/Polling向两个Peer Endpoint发送一次消息，释放前保存各自数据和Pending。
# 2. 逐个释放Destination，期间Source不得ACK；最后显式ACK才允许Source收到数据。
#
# 通过条件：
# 1. 两目标数据相同、首个释放保留另一目标；显式ACK之前Source无Pending，之后原数据正确。
def test_ipcm_p1_007_multi_destination(ipcm_support, resource_driver, record_property):

    # 准备：角色来自Capability和Execution Mapping，不绑定芯片实例或IRQ编号。
    support = ipcm_support
    local, peer = support.local, support.peer
    source, destination = support.local_endpoint, support.peer_endpoint
    require_evidence(record_property, "dut", "peer")
    support.require("multi_destination", "polling")

    # 隔离：先停止两核Service，再复位本IP和整池资源；所有配置必须在此之后。
    local.peer_cancel(expected_identity=support.peer_identity)
    local.state_reset()
    support.crg.reset(CrgPeripheral.IPCM, instance=local.instance_id)
    peer.state_reset()
    resource_driver.reset()

    second = support.second_endpoint
    length = min(7, support.capacity)
    payload = pattern(length, 0x71)
    deadline = OperationDeadline.start(8.0, label="IPCM_P1_007")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 配置：两个Destination由独立Peer分别轮询，不启用未经确认的AUTO聚合ACK。
        local.configure(
            IpcmConfig(
                0,
                1,
                source,
                frozenset((destination, second)),
                frozenset(),
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
            irq=False,
            stage=IpcmEventStage.MESSAGE,
            timeout_s=deadline.remaining_s(),
        )
        peer.capture_arm(
            1,
            second,
            0,
            length,
            irq=False,
            stage=IpcmEventStage.MESSAGE,
            timeout_s=deadline.remaining_s(),
        )
        local.capture_arm(
            0,
            source,
            0,
            length,
            irq=False,
            stage=IpcmEventStage.ACK,
            timeout_s=deadline.remaining_s(),
        )

        # 发送与双目标观测：任何DCLEAR之前必须完整取回两个Endpoint消息。
        local.payload_write(0, 1, payload, timeout_s=deadline.remaining_s())
        local.message_send(0, timeout_s=deadline.remaining_s())
        first_event = peer.capture_wait(0, timeout_s=deadline.remaining_s())
        second_event = peer.capture_wait(1, timeout_s=deadline.remaining_s())
        record_property(
            "destination_a_event_count", int(first_event.state is IpcmCaptureState.READY)
        )
        record_property(
            "destination_b_event_count", int(second_event.state is IpcmCaptureState.READY)
        )
        record_property(
            "destination_payload_match", first_event.payload == second_event.payload == payload
        )
        record_observation(
            record_property,
            key="destination_a_raw",
            value=first_event.raw_status,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL_A.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="destination_b_raw",
            value=second_event.raw_status,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL_B.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="destination_a_payload",
            value=first_event.payload,
            source="peer",
            device_id="ipcm_peer",
            endpoint="MESSAGE_A.RECEIVED_PAYLOAD",
        )
        record_observation(
            record_property,
            key="destination_b_payload",
            value=second_event.payload,
            source="peer",
            device_id="ipcm_peer",
            endpoint="MESSAGE_B.RECEIVED_PAYLOAD",
        )

        assert event_matches(first_event, payload, 0, destination, irq=False)
        assert event_matches(second_event, payload, 0, second, irq=False)

        # 首次释放：只去掉第一个目标，不调用全Mailbox清除。
        peer.destination_release(0, destination, timeout_s=deadline.remaining_s())
        after_first = peer.mailbox_snapshot_get(0, timeout_s=deadline.remaining_s())
        source_first = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
        first_pending = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        second_pending = peer.pending_snapshot_get(second, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="status_after_first_release",
            value=endpoint_mask(after_first.destination_endpoints),
            source="peer",
            device_id="ipcm_peer",
            endpoint="MAILBOX.DESTINATION_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="source_raw_after_first_release",
            value=source_first.raw_pending,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="first_target_raw_after_release",
            value=first_pending.raw_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL_A.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="second_target_raw_after_release",
            value=second_pending.raw_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL_B.RAW_PENDING_MAILBOXES",
        )

        assert after_first.destination_endpoints == frozenset((second,))
        assert (
            source_first.raw_pending
            == source_first.masked_pending
            == first_pending.raw_pending
            == first_pending.masked_pending
            == second_pending.masked_pending
            == 0
        )
        assert second_pending.raw_pending == 1

        # 第二次释放：全部Destination为空，MANUAL仍不得自动ACK。
        peer.destination_release(0, second, timeout_s=deadline.remaining_s())
        after_final = peer.mailbox_snapshot_get(0, timeout_s=deadline.remaining_s())
        before_ack = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="status_after_final_release",
            value=endpoint_mask(after_final.destination_endpoints),
            source="peer",
            device_id="ipcm_peer",
            endpoint="MAILBOX.DESTINATION_ENDPOINTS",
        )
        record_observation(
            record_property,
            key="source_raw_before_ack",
            value=before_ack.raw_pending,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )

        assert not after_final.destination_endpoints
        assert before_ack.raw_pending == before_ack.masked_pending == 0

        # 显式ACK：只在两个目标均已释放之后执行，保留Source实际Payload。
        peer.ack_send(0, timeout_s=deadline.remaining_s())
        ack = local.capture_wait(0, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="source_raw_on_ack",
            value=ack.raw_status,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="final_ack_payload",
            value=ack.payload,
            source="dut",
            endpoint="ACK.RECEIVED_PAYLOAD",
        )

        final_ack_data_match = ack.payload == payload
        record_property("final_ack_data_match", final_ack_data_match)
        assert final_ack_data_match
        assert event_matches(ack, payload, 0, source, irq=False)
        local.interrupt_clear(0, timeout_s=deadline.remaining_s())
        final = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
        record_property("final_pending", [final.raw_pending, final.masked_pending])
        assert final.raw_pending == final.masked_pending == 0


# 测试 Feature：
# AUTO模式下显式ACK，不通过切模式或释放Destination绕过目标Feature。
#
# 测试方法：
# 1. 读回AUTO与Destination存在，再由Peer直接发送ACK。
# 2. 保存原数据ACK，清除后重新武装并观察100ms，检查无第二次ACK。
#
# 通过条件：
# 1. AUTO始终不变、原Payload正确；ACK仅一次，重新武装后无Raw/Masked及回调。
def test_ipcm_p1_008_explicit_ack_in_auto(ipcm_support, resource_driver, record_property):

    # 准备：角色来自Capability和Execution Mapping，不绑定芯片实例或IRQ编号。
    support = ipcm_support
    local, peer = support.local, support.peer
    source, destination = support.local_endpoint, support.peer_endpoint
    require_evidence(record_property, "dut", "peer")
    support.require("explicit_ack_in_auto")

    # 隔离：先停止两核Service，再复位本IP和整池资源；所有配置必须在此之后。
    local.peer_cancel(expected_identity=support.peer_identity)
    local.state_reset()
    support.crg.reset(CrgPeripheral.IPCM, instance=local.instance_id)
    peer.state_reset()
    resource_driver.reset()

    length = min(7, support.capacity)
    payload = pattern(length, 0x81)
    deadline = OperationDeadline.start(5.0, label="IPCM_P1_008")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 配置：AUTO并打开两端IRQ，硬件读回用于证明没有偷换MANUAL。
        local.configure(
            IpcmConfig(
                0,
                1,
                source,
                frozenset((destination,)),
                frozenset((source, destination)),
                IpcmAckMode.AUTO,
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
        local.payload_write(0, 1, payload, timeout_s=deadline.remaining_s())
        local.message_send(0, timeout_s=deadline.remaining_s())
        message = peer.capture_wait(0, timeout_s=deadline.remaining_s())
        before = peer.mailbox_snapshot_get(0, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="mode_before_ack",
            value=before.ack_mode.name,
            source="peer",
            device_id="ipcm_peer",
            endpoint="MAILBOX.ACK_MODE",
        )
        record_observation(
            record_property,
            key="destination_before_ack",
            value=endpoint_mask(before.destination_endpoints),
            source="peer",
            device_id="ipcm_peer",
            endpoint="MAILBOX.DESTINATION_ENDPOINTS",
        )
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

        assert before.ack_mode is IpcmAckMode.AUTO and before.destination_endpoints == frozenset(
            (destination,)
        )
        assert event_matches(message, payload, 0, destination, irq=True)

        # 激励：唯一应答动作是ack_send；不得调用destination_release。
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

        record_property("ack_callback_delta", ack.callback_count)
        assert event_matches(ack, payload, 0, source, irq=True)

        # 重复检查：清ACK后重新使能IRQ，避免用ISR暂停投递来制造“没有重复”的假象。
        local.interrupt_clear(0, timeout_s=deadline.remaining_s())
        local.capture_arm(
            0,
            source,
            0,
            length,
            irq=True,
            stage=IpcmEventStage.ACK,
            timeout_s=deadline.remaining_s(),
        )
        repeated = local.capture_observe(0, window_s=0.1, timeout_s=deadline.remaining_s())
        final = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
        after = local.mailbox_snapshot_get(0, timeout_s=deadline.remaining_s())
        record_property("duplicate_callback_count", repeated.callback_count)
        record_observation(
            record_property,
            key="final_source_raw",
            value=final.raw_pending,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        assert repeated.state is IpcmCaptureState.WAITING and repeated.callback_count == 0
        assert final.raw_pending == final.masked_pending == 0
        assert after.ack_mode is IpcmAckMode.AUTO
