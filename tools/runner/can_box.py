# CAN盒子人工诊断入口。
# 职责：读取同一run_config.yaml，调用正式仪器Adapter做配置、收发或身份检查。
# 边界：不实现DUT Case，不烧录，不把诊断输出记录为正式HIL结论。
# 依赖：已安装的et_test_platform包、PyYAML和标准库。

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

import yaml
from et_test_platform.instruments.can_boxes import CanBusConfig, CanFrame
from et_test_platform.instruments.can_boxes.connection import create_zlg_can_box


# 默认只校验配置；执行硬件命令还要求配置中的confirm_hardware_actions为true。
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CAN box operator diagnostics (not Formal HIL)")
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).resolve().parents[2] / "run_config.yaml"
    )
    parser.add_argument("--device", default="can_box")
    parser.add_argument("--action", choices=("check", "info", "send", "receive"), default="check")
    parser.add_argument("--nominal-bitrate", type=int, default=500_000)
    parser.add_argument("--data-bitrate", type=int, default=2_000_000)
    parser.add_argument("--listen-only", action="store_true")
    parser.add_argument("--non-iso", action="store_true")
    parser.add_argument("--id", type=lambda value: int(value, 0), default=0x123)
    parser.add_argument("--data", default="", help="hexadecimal bytes; no implicit padding")
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--fd", action="store_true")
    parser.add_argument("--brs", action="store_true")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--dlc", type=int)
    parser.add_argument("--timeout-s", type=float, default=1.0)
    args = parser.parse_args(argv)
    try:
        config_path = args.config.resolve(strict=True)
        config = yaml.safe_load(config_path.read_text(encoding="utf-8-sig"))
        entry = config["instruments"][args.device]
        if entry.get("enabled") is not True or entry.get("driver") != "zlg_can":
            raise ValueError("selected instrument must be enabled with driver zlg_can")
        box = create_zlg_can_box(entry["connection"], base=config_path.parent)
        if not box.connection.library.is_file():
            raise FileNotFoundError(box.connection.library)
        bus = CanBusConfig(args.nominal_bitrate, args.data_bitrate, args.listen_only, args.non_iso)
        frame = CanFrame(
            args.id,
            bytes.fromhex(args.data),
            extended=args.extended,
            fd=args.fd,
            brs=args.brs,
            remote=args.remote,
            dlc=args.dlc,
        )
        if args.action == "check":
            print(f"CAN box configuration valid: {box.identity}; no hardware opened")
            return 0
        if config.get("pipeline", {}).get("confirm_hardware_actions") is not True:
            raise ValueError("pipeline.confirm_hardware_actions must be true")
        # 打开后总是关闭；若主操作和关闭同时失败，二者均保留在异常链。
        try:
            info = box.open()
            print(json.dumps({"diagnostic": True, "device": asdict(info)}, ensure_ascii=False))
            if args.action != "info":
                box.configure(bus)
                if args.action == "send":
                    box.send(frame)
                    print("1 frame accepted by SDK; bus completion is NOT verified")
                else:
                    received = box.receive(timeout_s=args.timeout_s)
                    record = asdict(received)
                    record["frame"]["data"] = list(received.frame.data)
                    print(json.dumps({"diagnostic": True, "received": record}, ensure_ascii=False))
        except BaseException as primary:
            try:
                box.close()
            except Exception as cleanup:
                raise RuntimeError(f"CAN box cleanup also failed: {cleanup}") from primary
            raise
        else:
            box.close()
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        print(f"CAN box diagnostic failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
