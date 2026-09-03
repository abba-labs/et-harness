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
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation, require_evidence
from ..case_cleanup import case_cleanup_scope
from .ipcm_helpers import endpoint_mask, event_matches, first_mismatch, pattern

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
# Linked链与连续分段
# =============================================================================


# 测试 Feature：
# Auto Link Manual ACK连续Mailbox长Payload。
#
# 测试方法：
# 1. 按Capability选择最大连续链，读回所有成员与末项Link终止，发送N*C-3字节。
# 2. Peer逐项锁存；先武装下一项，再发送当前项ACK推进硬件链。
# 3. PC重组并逐字节比较，Source只允许一次链尾ACK。
#
# 通过条件：
# 1. N次Peer消息顺序与数据正确，Source为一次链尾ACK，全部终态Pending为0。
def test_ipcm_p2_001_manual_ack_link(
    ipcm_support, resource_driver, record_property, et_artifact_dir
):

    # 准备：角色来自Capability和Execution Mapping，不绑定芯片实例或IRQ编号。
    support = ipcm_support
    local, peer = support.local, support.peer
    source, destination = support.local_endpoint, support.peer_endpoint
    require_evidence(record_property, "dut", "peer")
    support.require("auto_link")

    # 隔离：先停止两核Service，再复位本IP和整池资源；所有配置必须在此之后。
    local.peer_cancel(expected_identity=support.peer_identity)
    local.state_reset()
    support.crg.reset(CrgPeripheral.IPCM, instance=local.instance_id)
    peer.state_reset()
    resource_driver.reset()

    count, capacity = support.mailbox_count, support.capacity
    record_property("linked_range", f"0..{count - 1}")
    assert count >= 2 and capacity >= 4
    payload = pattern(count * capacity - 3, 0x91)
    tail_length = capacity - 3
    chunks = []
    events = []
    deadline = OperationDeadline.start(15.0, label="IPCM_P2_001")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 链配置：总成员数包括首Mailbox，尾项必须关闭Link；每个读回独立保存。
        local.configure(
            IpcmConfig(
                0,
                count,
                source,
                frozenset((destination,)),
                frozenset((source, destination)),
                IpcmAckMode.MANUAL,
                IpcmLinkMode.LINKED,
            ),
            timeout_s=deadline.remaining_s(),
        )

        # 观测：逐Mailbox检查ACK/Link与两端路由，保留尾项不链接的独立证据。
        for mailbox in range(count):
            config = local.mailbox_snapshot_get(mailbox, timeout_s=deadline.remaining_s())
            write_json_result(
                et_artifact_dir / f"link_config_{mailbox}.json",
                {
                    "mailbox": mailbox,
                    "ack_mode": config.ack_mode.name,
                    "link_mode": config.link_mode.name,
                    "source": endpoint_mask(config.source_endpoints),
                    "destination": endpoint_mask(config.destination_endpoints),
                },
            )
            assert config.ack_mode is IpcmAckMode.MANUAL
            assert config.link_mode is (
                IpcmLinkMode.LINKED if mailbox + 1 < count else IpcmLinkMode.SINGLE
            )
            assert config.source_endpoints == frozenset(
                (source,)
            ) and config.destination_endpoints == frozenset((destination,))

        # 武装与发送：Source只等待尾项，但若中间项错误地产生Source IRQ仍会被Service识别为异常。
        peer.capture_arm(
            0,
            destination,
            0,
            capacity,
            irq=True,
            stage=IpcmEventStage.MESSAGE,
            timeout_s=deadline.remaining_s(),
        )
        local.capture_arm(
            0,
            source,
            count - 1,
            tail_length,
            irq=True,
            stage=IpcmEventStage.ACK,
            timeout_s=deadline.remaining_s(),
        )
        local.payload_write(0, count, payload, timeout_s=deadline.remaining_s())
        local.message_send(0, timeout_s=deadline.remaining_s())

        # 链推进：先保存当前事件，再为下一Mailbox武装；顺序不可反过来，否则IRQ可能先到。

        # 观测：逐Mailbox检查ACK/Link与两端路由，保留尾项不链接的独立证据。
        for mailbox in range(count):
            expected = payload[mailbox * capacity : (mailbox + 1) * capacity]
            message = peer.capture_wait(0, timeout_s=deadline.remaining_s())
            chunks.append(message.payload)
            events.append(message.mailbox)
            write_json_result(
                et_artifact_dir / f"link_event_{mailbox}.json",
                {
                    "mailbox": message.mailbox,
                    "raw": message.raw_status,
                    "masked": message.masked_status,
                    "callback_count": message.callback_count,
                    "payload": message.payload,
                },
            )
            record_observation(
                record_property,
                key=f"destination_raw_{mailbox}",
                value=message.raw_status,
                source="peer",
                device_id="ipcm_peer",
                endpoint=f"CHANNEL.RAW_PENDING_MAILBOXES[{mailbox}]",
            )
            assert event_matches(message, expected, mailbox, destination, irq=True)

            # 下一捕获必须在推进链之前就绪，当前事件已经存到PC，不再依赖被复用的Slot。
            if mailbox + 1 < count:
                next_length = min(capacity, len(payload) - (mailbox + 1) * capacity)
                peer.capture_arm(
                    0,
                    destination,
                    mailbox + 1,
                    next_length,
                    irq=True,
                    stage=IpcmEventStage.MESSAGE,
                    timeout_s=deadline.remaining_s(),
                )
            peer.ack_send(mailbox, timeout_s=deadline.remaining_s())

        # Source观测：只接受一次尾Mailbox ACK，不能把N次软件ACK动作当作N次Source中断。
        ack = local.capture_wait(0, timeout_s=deadline.remaining_s())
        reconstructed = b"".join(chunks)
        record_property("reconstructed_length", len(reconstructed))
        record_property("payload_data_match", reconstructed == payload)
        record_property("first_mismatch_offset", first_mismatch(reconstructed, payload))
        record_property("pending_sequence_match", events == list(range(count)))
        record_property("source_ack_mailbox", ack.mailbox)
        record_observation(
            record_property,
            key="source_ack_raw_pending",
            value=ack.raw_status,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="source_ack_masked_pending",
            value=ack.masked_status,
            source="dut",
            endpoint="CHANNEL.MASKED_PENDING_MAILBOXES",
        )
        record_property("source_ack_count", ack.callback_count)
        write_json_result(
            et_artifact_dir / "linked_payload.json",
            {
                "expected": payload,
                "actual": reconstructed,
                "mailbox_sequence": events,
                "ack_payload": ack.payload,
            },
        )
        assert reconstructed == payload
        assert events == list(range(count))
        assert event_matches(ack, payload[-tail_length:], count - 1, source, irq=True)

        # 终态：清尾ACK后读取两核的全Mailbox位集合，不能遗漏中间链成员残留。
        local.interrupt_clear(count - 1, timeout_s=deadline.remaining_s())
        final = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
        peer_final = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="final_source_raw",
            value=final.raw_pending,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="final_peer_raw",
            value=peer_final.raw_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_property(
            "final_pending_clear",
            final.raw_pending
            == final.masked_pending
            == peer_final.raw_pending
            == peer_final.masked_pending
            == 0,
        )
        assert (
            final.raw_pending
            == final.masked_pending
            == peer_final.raw_pending
            == peer_final.masked_pending
            == 0
        )


# 测试 Feature：
# Auto ACK Link连续Mailbox长Payload。
#
# 测试方法：
# 1. 按Capability选择最大连续链，读回所有成员与末项Link终止，发送N*C-3字节。
# 2. Peer逐项锁存；先武装下一项，再释放当前Destination推进硬件链。
# 3. PC重组并逐字节比较，Source只允许一次链尾ACK。
#
# 通过条件：
# 1. N次Peer消息顺序与数据正确，Source为一次链尾ACK，全部终态Pending为0。
def test_ipcm_p2_002_auto_ack_link(ipcm_support, resource_driver, record_property, et_artifact_dir):

    # 准备：角色来自Capability和Execution Mapping，不绑定芯片实例或IRQ编号。
    support = ipcm_support
    local, peer = support.local, support.peer
    source, destination = support.local_endpoint, support.peer_endpoint
    require_evidence(record_property, "dut", "peer")
    support.require("auto_ack_link")

    # 隔离：先停止两核Service，再复位本IP和整池资源；所有配置必须在此之后。
    local.peer_cancel(expected_identity=support.peer_identity)
    local.state_reset()
    support.crg.reset(CrgPeripheral.IPCM, instance=local.instance_id)
    peer.state_reset()
    resource_driver.reset()

    count, capacity = support.mailbox_count, support.capacity
    assert count >= 2 and capacity >= 4
    payload = pattern(count * capacity - 3, 0xA1)
    tail_length = capacity - 3
    chunks = []
    events = []
    deadline = OperationDeadline.start(15.0, label="IPCM_P2_002")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 链配置：总成员数包括首Mailbox，尾项必须关闭Link；每个读回独立保存。
        local.configure(
            IpcmConfig(
                0,
                count,
                source,
                frozenset((destination,)),
                frozenset((source, destination)),
                IpcmAckMode.AUTO,
                IpcmLinkMode.LINKED,
            ),
            timeout_s=deadline.remaining_s(),
        )

        # 观测：逐Mailbox检查ACK/Link与路由，确认尾Mailbox关闭链接。
        for mailbox in range(count):
            config = local.mailbox_snapshot_get(mailbox, timeout_s=deadline.remaining_s())
            write_json_result(
                et_artifact_dir / f"link_config_{mailbox}.json",
                {
                    "mailbox": mailbox,
                    "ack_mode": config.ack_mode.name,
                    "link_mode": config.link_mode.name,
                    "source": endpoint_mask(config.source_endpoints),
                    "destination": endpoint_mask(config.destination_endpoints),
                },
            )
            assert config.ack_mode is IpcmAckMode.AUTO
            assert config.link_mode is (
                IpcmLinkMode.LINKED if mailbox + 1 < count else IpcmLinkMode.SINGLE
            )
            assert config.source_endpoints == frozenset(
                (source,)
            ) and config.destination_endpoints == frozenset((destination,))

        # 武装与发送：Source只等待尾项，但若中间项错误地产生Source IRQ仍会被Service识别为异常。
        peer.capture_arm(
            0,
            destination,
            0,
            capacity,
            irq=True,
            stage=IpcmEventStage.MESSAGE,
            timeout_s=deadline.remaining_s(),
        )
        local.capture_arm(
            0,
            source,
            count - 1,
            tail_length,
            irq=True,
            stage=IpcmEventStage.ACK,
            timeout_s=deadline.remaining_s(),
        )
        local.payload_write(0, count, payload, timeout_s=deadline.remaining_s())
        local.message_send(0, timeout_s=deadline.remaining_s())

        # 链推进：先保存当前事件，再为下一Mailbox武装；顺序不可反过来，否则IRQ可能先到。
        for mailbox in range(count):
            expected = payload[mailbox * capacity : (mailbox + 1) * capacity]
            message = peer.capture_wait(0, timeout_s=deadline.remaining_s())
            chunks.append(message.payload)
            events.append(message.mailbox)
            write_json_result(
                et_artifact_dir / f"link_event_{mailbox}.json",
                {
                    "mailbox": message.mailbox,
                    "raw": message.raw_status,
                    "masked": message.masked_status,
                    "callback_count": message.callback_count,
                    "payload": message.payload,
                },
            )
            record_observation(
                record_property,
                key=f"destination_raw_{mailbox}",
                value=message.raw_status,
                source="peer",
                device_id="ipcm_peer",
                endpoint=f"CHANNEL.RAW_PENDING_MAILBOXES[{mailbox}]",
            )
            assert event_matches(message, expected, mailbox, destination, irq=True)

            # 下一捕获必须在推进链之前就绪，当前事件已经存到PC，不再依赖被复用的Slot。
            if mailbox + 1 < count:
                next_length = min(capacity, len(payload) - (mailbox + 1) * capacity)
                peer.capture_arm(
                    0,
                    destination,
                    mailbox + 1,
                    next_length,
                    irq=True,
                    stage=IpcmEventStage.MESSAGE,
                    timeout_s=deadline.remaining_s(),
                )
            peer.destination_release(mailbox, destination, timeout_s=deadline.remaining_s())
            released = peer.mailbox_snapshot_get(mailbox, timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key=f"released_destination_{mailbox}",
                value=endpoint_mask(released.destination_endpoints),
                source="peer",
                device_id="ipcm_peer",
                endpoint=f"MAILBOX[{mailbox}].DESTINATION_ENDPOINTS",
            )
            assert not released.destination_endpoints

        # Source观测：只接受一次尾Mailbox ACK，不能把N次软件ACK动作当作N次Source中断。
        ack = local.capture_wait(0, timeout_s=deadline.remaining_s())
        reconstructed = b"".join(chunks)
        record_property("linked_range", f"0..{count - 1}")
        record_property("reconstructed_length", len(reconstructed))
        record_property("payload_data_match", reconstructed == payload)
        record_property("first_mismatch_offset", first_mismatch(reconstructed, payload))
        record_property("destination_release_sequence_match", events == list(range(count)))
        record_property("source_ack_mailbox", ack.mailbox)
        record_observation(
            record_property,
            key="source_ack_raw_pending",
            value=ack.raw_status,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="source_ack_masked_pending",
            value=ack.masked_status,
            source="dut",
            endpoint="CHANNEL.MASKED_PENDING_MAILBOXES",
        )
        record_property("source_ack_count", ack.callback_count)
        write_json_result(
            et_artifact_dir / "linked_payload.json",
            {
                "expected": payload,
                "actual": reconstructed,
                "mailbox_sequence": events,
                "ack_payload": ack.payload,
            },
        )
        assert reconstructed == payload
        assert events == list(range(count))
        assert event_matches(ack, payload[-tail_length:], count - 1, source, irq=True)

        # 终态：清尾ACK后读取两核的全Mailbox位集合，不能遗漏中间链成员残留。
        local.interrupt_clear(count - 1, timeout_s=deadline.remaining_s())
        final = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
        peer_final = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="final_source_raw",
            value=final.raw_pending,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="final_peer_raw",
            value=peer_final.raw_pending,
            source="peer",
            device_id="ipcm_peer",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_property(
            "final_pending_clear",
            final.raw_pending
            == final.masked_pending
            == peer_final.raw_pending
            == peer_final.masked_pending
            == 0,
        )
        assert (
            final.raw_pending
            == final.masked_pending
            == peer_final.raw_pending
            == peer_final.masked_pending
            == 0
        )


# 测试 Feature：
# 同Mailbox分段传输与连续复用。
#
# 测试方法：
# 1. 一次配置MANUAL/SINGLE；3*C+3字节拆成C、C、C、3四段。
# 2. 每段完成消息与ACK后清除，再发下一段，中间不整IP复位；最后发送独立短Payload。
#
# 通过条件：
# 1. 各段数据和顺序准确，重组等于原Payload，短消息复用正确，终态无Pending。
def test_ipcm_p2_003_segmented_reuse(
    ipcm_support, resource_driver, record_property, et_artifact_dir
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

    capacity = support.capacity
    assert capacity >= 4
    payload = pattern(3 * capacity + 3, 0xB1)
    segments = [payload[offset : offset + capacity] for offset in range(0, len(payload), capacity)]
    reuse_payload = pattern(min(7, capacity), 0xC1)
    reconstructed = bytearray()
    sequence = []
    deadline = OperationDeadline.start(12.0, label="IPCM_P2_003")
    with case_cleanup_scope(lambda: cleanup_actions(support, resource_driver)):
        # 配置：只配置一次；后续重新ARM负责恢复ISR暂停的IRQ，而不是通过复位掩盖复用问题。
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

        # 分段与末次复用：前四笔是总Payload分段，最后一笔是独立短消息。
        for index, segment in enumerate((*segments, reuse_payload)):
            peer.capture_arm(
                0,
                destination,
                0,
                len(segment),
                irq=True,
                stage=IpcmEventStage.MESSAGE,
                timeout_s=deadline.remaining_s(),
            )
            local.capture_arm(
                0,
                source,
                0,
                len(segment),
                irq=True,
                stage=IpcmEventStage.ACK,
                timeout_s=deadline.remaining_s(),
            )
            local.payload_write(0, 1, segment, timeout_s=deadline.remaining_s())
            local.message_send(0, timeout_s=deadline.remaining_s())
            message = peer.capture_wait(0, timeout_s=deadline.remaining_s())

            # 每段必须先记录原消息，再ACK；失败现场按段保存，不覆盖上一段。
            peer.ack_send(0, timeout_s=deadline.remaining_s())
            ack = local.capture_wait(0, timeout_s=deadline.remaining_s())
            write_json_result(
                et_artifact_dir / f"segment_{index}.json",
                {
                    "sequence": index,
                    "length": len(segment),
                    "message": message.payload,
                    "ack": ack.payload,
                    "message_raw": message.raw_status,
                    "message_masked": message.masked_status,
                    "ack_raw": ack.raw_status,
                    "ack_masked": ack.masked_status,
                    "message_count": message.callback_count,
                    "ack_count": ack.callback_count,
                },
            )
            record_observation(
                record_property,
                key=f"segment_payload_{index}",
                value=message.payload,
                source="peer",
                device_id="ipcm_peer",
                endpoint=f"MESSAGE.RECEIVED_PAYLOAD[{index}]",
            )
            record_observation(
                record_property,
                key=f"segment_ack_{index}",
                value=ack.payload,
                source="dut",
                endpoint=f"ACK.RECEIVED_PAYLOAD[{index}]",
            )
            if index < len(segments):
                reconstructed.extend(message.payload)
                sequence.append(index)
            else:
                record_property("reuse_data_match", message.payload == ack.payload == reuse_payload)
            assert event_matches(message, segment, 0, destination, irq=True)
            assert event_matches(ack, segment, 0, source, irq=True)
            local.interrupt_clear(0, timeout_s=deadline.remaining_s())

        # 重组与终态：PC才负责比较Expected和完成顺序，固件不返回预制PASS。
        final = local.pending_snapshot_get(source, timeout_s=deadline.remaining_s())
        peer_final = peer.pending_snapshot_get(destination, timeout_s=deadline.remaining_s())
        record_property("actual_segment_count", len(sequence))
        record_property("segment_sequence_match", sequence == list(range(len(segments))))
        record_property("reconstructed_length", len(reconstructed))
        record_property("payload_data_match", reconstructed == payload)
        record_property("first_mismatch_offset", first_mismatch(bytes(reconstructed), payload))
        record_observation(
            record_property,
            key="final_raw_pending",
            value=final.raw_pending,
            source="dut",
            endpoint="CHANNEL.RAW_PENDING_MAILBOXES",
        )
        record_observation(
            record_property,
            key="final_masked_pending",
            value=final.masked_pending,
            source="dut",
            endpoint="CHANNEL.MASKED_PENDING_MAILBOXES",
        )
        write_json_result(
            et_artifact_dir / "segmented_payload.json",
            {"actual": bytes(reconstructed), "expected": payload, "sequence": sequence},
        )
        assert len(sequence) == len(segments) == 4
        assert sequence == list(range(len(segments))) and reconstructed == payload
        assert (
            final.raw_pending
            == final.masked_pending
            == peer_final.raw_pending
            == peer_final.masked_pending
            == 0
        )
