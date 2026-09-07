# CAN外部链路人工诊断，不属于Formal Case。
# 职责：复用当前配置、CAN/GPIO Driver和CAN盒子，保持DUT外部回环，执行盒子只听/ACK/只听对照。
# 边界：不烧录、不改注册表、不生成正式PASS；完整现场只写当前Artifact Run。
# 依赖：既有Pipeline配置/互斥锁、芯片映射与设备Adapter。

from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import asdict, is_dataclass
from importlib import import_module
from pathlib import Path

from artifact_layout import (
    capture_source_identity,
    create_run_directory,
    utc_timestamp,
    write_manifest,
)
from et_test_platform.drivers.can import (
    CanBusConfig,
    CanDriver,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanLoopback,
    CanOptions,
    CanPhaseTiming,
    CanRamLayout,
    CanRxSource,
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanTxFrame,
    CanUnmatchedPolicy,
)
from et_test_platform.drivers.crg import CrgDriver, CrgPeripheral
from et_test_platform.drivers.framework import FrameworkDriver
from et_test_platform.drivers.gpio import GpioDriver, GpioFunction
from et_test_platform.drivers.resource import ResourceDriver
from et_test_platform.instruments.can_boxes.connection import create_zlg_can_box
from et_test_platform.instruments.can_boxes.models import CanBusConfig as BoxBusConfig
from et_test_platform.profiles.bench import load_serial_target
from et_test_platform.profiles.capabilities import load_packaged_chip_capabilities
from et_test_platform.profiles.hardware_connections import load_hardware_connections
from et_test_platform.scheduling.target_connection import create_serial_target_client
from run_pipeline import REPOSITORY_ROOT, _load_context, _pipeline_lock

PAYLOAD = bytes.fromhex("01 23 45 67 89 AB CD EF")
OBSERVE_SECONDS = 5.0


# 序列化真实观测；字节以HEX展示，数据类保留每个字段，不输出对象地址。
def _encode(value: object) -> object:
    if isinstance(value, bytes):
        return value.hex(" ").upper()
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"unsupported diagnostic value: {type(value).__name__}")


# 配置外部回环CAN，保持IRQ Case的时序/过滤/模式；不调用Formal Case。
def _configure(can: CanDriver, mapping: object, bitrate: int) -> None:
    clock = mapping.CAN_CLOCK_HZ["fpga"]
    if clock % (bitrate * 20):
        raise ValueError("diagnostic bitrate is not representable by 20 TQ")
    phase = CanPhaseTiming(clock // (bitrate * 20), 15, 4, 4)
    can.initializing_set(True)
    can.wait_initializing(True, timeout_s=2.0)
    can.timing_set(CanTiming(phase, CanPhaseTiming(clock // (2_000_000 * 20), 15, 4, 4)))
    can.options_set(
        CanOptions(
            fd_enabled=False,
            brs_enabled=False,
            automatic_retry=True,
            tx_pause=False,
            edge_filter=False,
            protocol_exception=True,
            tdc_enabled=False,
            tdc_offset_cycles=0,
            tdc_filter_cycles=0,
            ram_watchdog_cycles=0,
        )
    )

    # 一个TX、四项RX0；按芯片元素头大小计算偏移，保留Dedicated RX空间。
    tx = mapping.CAN_STD_FILTER_BYTES
    stride = mapping.CAN_RAM_HEADER_BYTES + len(PAYLOAD)
    rx = tx + stride
    buffers = rx + 4 * stride
    limits = can.ram_limits_get()
    if buffers + limits.rx_buffer_count * stride > limits.ram_bytes:
        raise ValueError("diagnostic RAM layout exceeds capacity")
    can.ram_layout_set(
        CanRamLayout(
            std_offset=0,
            std_count=1,
            ext_offset=tx,
            ext_count=0,
            tx_offset=tx,
            tx_buffer_count=1,
            tx_fifo_count=0,
            tx_queue=False,
            tx_payload_bytes=8,
            event_offset=rx,
            event_count=0,
            event_watermark=0,
            rx0_offset=rx,
            rx0_count=4,
            rx0_watermark=0,
            rx0_overwrite=False,
            rx1_offset=buffers,
            rx1_count=0,
            rx1_watermark=0,
            rx1_overwrite=False,
            rx_buffer_offset=buffers,
            rx_buffer_payload_bytes=8,
            rx0_payload_bytes=8,
            rx1_payload_bytes=8,
        )
    )
    can.filter_set(
        0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x321), extended=False
    )
    can.loopback_set(CanLoopback.EXTERNAL)
    can.bus_config_set(
        CanBusConfig(
            monitor=False,
            restricted=False,
            timestamp_divisor=1,
            timestamp_source=CanTimestampSource.DISABLED,
            timeout_source=CanTimeoutSource.CONTINUOUS,
            timeout_period=0,
            timeout_enabled=False,
            reject_remote_ext=True,
            reject_remote_std=True,
            unmatched_ext=CanUnmatchedPolicy.REJECT,
            unmatched_std=CanUnmatchedPolicy.REJECT,
        )
    )
    can.tx_buffer_irq_set(0, True)
    can.initializing_set(False)
    can.wait_initializing(False, timeout_s=2.0)


# 同一外部回环配置比较盒子ACK参与方式；超时作为诊断现场，不形成Formal PASS。
def _observe(can: CanDriver, box: object, direction: str) -> dict[str, object]:
    loopback = can.loopback_get()
    bus = can.bus_config_get()
    if loopback != CanLoopback.EXTERNAL or bus.monitor:
        raise RuntimeError("diagnostic requires actual EXTERNAL loopback with MON disabled")
    initial_error = box.error_get()
    can.tx_write(0, CanTxFrame(0x123, CanFrameFlags.NONE, len(PAYLOAD), 0, PAYLOAD))
    can.tx_request(1)
    tx = can.wait_tx_complete(1, timeout_s=OBSERVE_SECONDS)
    error_after_tx = box.error_get()
    captured = None
    capture_error = None
    try:
        captured = box.receive(timeout_s=OBSERVE_SECONDS)
    except TimeoutError as error:
        # 保留真实超时文本；不重试、不将空接收转换成通过。
        capture_error = str(error)
    rx = can.rx_fifo_status_get(0)
    received = None
    if rx.fill:
        received = can.rx_read(CanRxSource.FIFO0)
        can.rx_fifo_ack(0, received.index)
    return {
        "diagnostic_only": True,
        "scenario": direction,
        "peer_listen_only": direction != "ack_enabled",
        "loopback_readback": int(loopback),
        "bus_readback": bus,
        "box_error_before_tx": initial_error,
        "box_error_after_tx": error_after_tx,
        "tx": tx,
        "peer_capture": captured,
        "capture_error": capture_error,
        "dut_rx_status": rx,
        "dut_rx_frame": received,
        "irq": can.irq_snapshot_get(),
        "protocol": can.protocol_status_consume(),
        "box_error_final": box.error_get(),
    }


# 默认只检查配置；--execute明确执行已批准的非烧录诊断，输出不纳入正式报告。
def main() -> int:
    parser = argparse.ArgumentParser(description="CAN external ACK comparison, NOT Formal HIL")
    parser.add_argument("--config", type=Path, default=REPOSITORY_ROOT / "run_config.yaml")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    context = _load_context(args.config.resolve())
    if context.config["target"]["kind"] != "fpga":
        raise ValueError("this diagnostic currently requires an FPGA clock mapping")
    entry = context.config["instruments"]["can_box"]
    if not entry["enabled"] or entry["driver"] != "zlg_can":
        raise ValueError("enable the explicit zlg_can instrument in run_config.yaml")
    box = create_zlg_can_box(entry["connection"], base=context.config_path.parent)
    if not args.execute:
        print(f"Configuration ready: {box.identity}; NO hardware opened")
        return 0
    if not context.config["pipeline"]["confirm_hardware_actions"]:
        raise ValueError("hardware confirmation is not enabled")

    with _pipeline_lock():
        os.environ.update(context.environment)
        run = create_run_directory(context.output_root, run_name="can_external_ack_diagnostic")
        stage = run / "stages" / "can_external_ack_diagnostic"
        stage.mkdir(parents=True)
        (run / "config").mkdir()
        shutil.copy2(context.config_path, run / "config" / "run_config.snapshot.yaml")
        revision, dirty = capture_source_identity(REPOSITORY_ROOT)
        manifest = {
            "diagnostic_only": True,
            "status": "RUNNING",
            "source_revision": revision,
            "source_dirty": dirty,
            "started_at": utc_timestamp(),
        }
        write_manifest(run, manifest)
        print(f"Diagnostic output: {stage}", flush=True)
        target_config = load_serial_target(
            context.bench_path, context.config["target"]["logical_name"]
        )
        target = create_serial_target_client(target_config)
        try:
            with target, (stage / "observations.jsonl").open("w", encoding="utf-8") as log:
                framework = FrameworkDriver(target)
                hello = framework.hello()
                if hello.chip_id != target_config.chip_id:
                    raise ValueError("HELLO chip does not match configured bench")
                framework.discover_services()
                capabilities = load_packaged_chip_capabilities(hello.chip_id)
                connections = load_hardware_connections(
                    capabilities=capabilities, expected_lane="fpga"
                )
                endpoint = connections.select("can")["can"]["dut"]
                instance = int(endpoint.handle.removeprefix("can"))
                mapping = import_module(
                    f"et_test_platform.profiles.chip_execution_mappings.{hello.chip_id}.can_routes"
                )
                can, crg, resource, gpio = (
                    CanDriver(target, instance),
                    CrgDriver(target),
                    ResourceDriver(target),
                    GpioDriver(target),
                )
                try:
                    identity = box.open()
                    log.write(
                        json.dumps(
                            {
                                "box": identity,
                                "handle": endpoint.handle,
                                "gpio": dict(endpoint.gpio),
                            },
                            default=_encode,
                        )
                        + "\n"
                    )
                    for direction in ("listen_before", "ack_enabled", "listen_after"):
                        # 先停止外部刺激，再复位CAN和资源；不复位控制UART的GPIO域。
                        box.stop()
                        crg.reset(CrgPeripheral.CAN, instance=instance)
                        resource.reset()
                        for signal, function in (
                            ("rx", GpioFunction.CAN_RX),
                            ("tx", GpioFunction.CAN_TX),
                        ):
                            gpio.configure_signal(endpoint.gpio[signal], function, instance)
                        box.configure(
                            BoxBusConfig(500_000, 2_000_000, listen_only=direction != "ack_enabled")
                        )
                        box.clear()
                        _configure(can, mapping, 500_000)
                        result = _observe(can, box, direction)
                        line = json.dumps(result, ensure_ascii=False, default=_encode)
                        log.write(line + "\n")
                        log.flush()
                        print(line, flush=True)
                finally:
                    # 嵌套finally保证关闭失败时仍尝试复位，异常链保留原始错误。
                    try:
                        box.close()
                    finally:
                        try:
                            crg.reset(CrgPeripheral.CAN, instance=instance)
                        finally:
                            resource.reset()
            manifest["status"] = "DIAGNOSTIC_COMPLETE"
            return 0
        except BaseException as error:
            manifest.update(status="ERROR", error=str(error))
            raise
        finally:
            manifest["finished_at"] = utc_timestamp()
            write_manifest(run, manifest)


if __name__ == "__main__":
    raise SystemExit(main())
