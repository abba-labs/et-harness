# 自动化平台命令行诊断入口。
#
# 职责：解析用户参数并调用稳定 Framework/Target API 完成最小软件诊断。
# 边界：不嵌入 IP 专用 Wire、不替代 pytest Formal Case，也不维护隐藏运行状态。
# 依赖：仅依赖 argparse 和平台稳定公共 API。

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from ..drivers.framework import FrameworkDriver
from ..profiles.bench import load_serial_target
from ..scheduling.target_connection import create_serial_target_client


# 执行 main 命令行入口；只组合稳定公共 API，参数或底层失败以明确退出状态报告。
def main(argv: Sequence[str] | None = None) -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Run Framework HELLO, VERSION_GET and SERVICE_LIST without executing an IP command."
        )
    )
    parser.add_argument("--bench", required=True, help="Bench profile YAML path")
    parser.add_argument("--target", default="dut", help="Target logical ID")
    args = parser.parse_args(argv)

    config = load_serial_target(args.bench, args.target)
    with create_serial_target_client(config) as target:
        framework = FrameworkDriver(target)
        hello = framework.hello()
        version = framework.version_get()
        services = framework.discover_services()

    print(
        json.dumps(
            {
                "transport": target.identity,
                "chip_id": hello.chip_id,
                "session_id": target.session_id,
                "protocol_version": version.protocol_version,
                "firmware_build_id": version.firmware_build_id,
                "registry_hash": hello.registry_hash,
                "services": [
                    {
                        "service_id": item.service_id,
                        "instance_id": item.instance_id,
                    }
                    for item in services
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
