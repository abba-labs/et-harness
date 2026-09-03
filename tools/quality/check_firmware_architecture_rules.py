#!/usr/bin/env python3
# Fail closed when Firmware Services regain cross-IP execution policy.

from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    from tools.quality.service_factory_contract import validated_factory_regions
except ModuleNotFoundError:
    from service_factory_contract import validated_factory_regions

_SERVICE_RE = re.compile(r"et_(?P<ip>[a-z0-9_]+)_service\.[ch]$")
_WRAP_RE = re.compile(r"et_(?P<ip>[a-z0-9_]+)_wrap\.c$")
_WRAP_INCLUDE_RE = re.compile(r'#include\s+"et_(?P<ip>[a-z0-9_]+)_wrap\.h"')
_DRIVER_INCLUDE_RE = re.compile(r'#include\s+"(?P<header>et6x_(?P<family>[a-z0-9_]+)\.h)"')
_SERVICE_SHARED_WRAP_ALLOWLIST = {"resource"}
_CROSS_IP_REGISTRY_TOKENS = (
    "resource_route",
    "route_lease",
    "endpoint_registry",
    "et_resource_wrap_publish_dma_endpoint",
    "et_resource_wrap_bind_dma_route",
)
_CHIP_CONFIG_NAME = "et_chip_wrap_config.h"
_CHIP_CONFIG_ALLOWED_SUFFIXES = (
    "_MAP_TABLE",
    "_FEATURE_FLAGS",
    "_STATUS_MASKS",
    "_LIMITS",
)
_WRAP_DRIVER_FAMILIES = {
    "aes": {"aes"},
    "cortex": {"cortex"},
    "crc": {"crc"},
    "crg": {"crg"},
    "dma": {"ahbdma"},
    "gpio": {"gpio"},
    "irq": {"interrupt"},
    "sysctrl": {"sysctrl"},
    # SDK的SYSCNT原子接口归属Cortex Driver；不接受其他IP Driver。
    "syscnt": {"cortex"},
    "uart": {"uart"},
}


# Format one Firmware governance violation with a stable diagnostic code.
def _violation(code: str, path: Path, message: str) -> str:
    return f"{path}: {code} {message}"


def check_file(path: Path) -> list[str]:
    match = _SERVICE_RE.search(path.name)
    if match is None:
        return []
    service_ip = match.group("ip")
    source = path.read_text(encoding="utf-8")
    errors: list[str] = []
    for include in _WRAP_INCLUDE_RE.finditer(source):
        wrap_ip = include.group("ip")
        if wrap_ip != service_ip and wrap_ip not in _SERVICE_SHARED_WRAP_ALLOWLIST:
            errors.append(
                _violation(
                    "ETFW101",
                    path,
                    f"service {service_ip} includes cross-IP wrap {wrap_ip}",
                )
            )
    if service_ip != "resource":
        for token in _CROSS_IP_REGISTRY_TOKENS:
            if token in source:
                errors.append(
                    _violation("ETFW102", path, f"cross-IP registry token is forbidden: {token}")
                )
    return errors


# Factory Marker只允许包围R300定义的include、声明和薄实现。
def check_service_factory_contract(path: Path) -> list[str]:
    match = _SERVICE_RE.search(path.name)
    if match is None:
        return []

    source = path.read_text(encoding="utf-8")
    _, factory_errors = validated_factory_regions(
        source,
        ip=match.group("ip"),
        suffix=path.suffix.lower(),
    )
    return [_violation("ETFW103", path, message) for message in factory_errors]


# 检查公共Wrap只包含本职责Chip Driver头文件，不把跨IP调用带入稳定适配层。
def check_wrap_driver_boundary(path: Path) -> list[str]:
    match = _WRAP_RE.fullmatch(path.name)
    if match is None:
        return []
    wrap_ip = match.group("ip")
    source = path.read_text(encoding="utf-8")
    allowed = _WRAP_DRIVER_FAMILIES.get(wrap_ip, {wrap_ip})
    errors: list[str] = []
    for include in _DRIVER_INCLUDE_RE.finditer(source):
        family = include.group("family")
        if family not in allowed:
            errors.append(
                _violation(
                    "ETFW201",
                    path,
                    f"wrap {wrap_ip} includes cross-IP driver {include.group('header')}",
                )
            )
    return errors


# 去除注释后检查Chip Config，避免把规则说明文字误判为实现逻辑。
def _without_c_comments(source: str) -> str:
    code = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//.*?$", "", code, flags=re.MULTILINE)


# Chip Config只能保存所有公共Wrap实际消费的编译期芯片事实。
def check_chip_wrap_config(path: Path, wrap_root: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    code = _without_c_comments(source)
    wrap_sources = "\n".join(
        item.read_text(encoding="utf-8") for item in sorted(wrap_root.glob("*.c"))
    )
    errors: list[str] = []

    if re.search(r"\b(?:if|switch|for|while)\s*\(", code):
        errors.append(
            _violation("ETFW301", path, "runtime control flow is forbidden in Chip Config")
        )
    if re.search(r"\b[A-Za-z_]\w*\s*\([^;{}]*\)\s*\{", code, flags=re.DOTALL):
        errors.append(
            _violation("ETFW302", path, "function definitions are forbidden in Chip Config")
        )
    if re.search(r"(?:^|_)(?:SERVICE|COMMAND|WIRE|CASE|PASS|FAIL)(?:_|\b)", code):
        errors.append(
            _violation("ETFW303", path, "protocol or Case semantics are forbidden in Chip Config")
        )
    if re.search(r"\b0x[0-9A-Fa-f]{8,}\b", code):
        errors.append(
            _violation("ETFW304", path, "raw physical addresses are forbidden in Chip Config")
        )
    if "#include" in code:
        errors.append(
            _violation(
                "ETFW305",
                path,
                "Chip Config must use build-selected Driver facts without includes",
            )
        )

    macro_names = re.findall(r"^#define\s+(ET_CHIP_[A-Z0-9_]+)\b", code, flags=re.MULTILINE)
    macro_names = [name for name in macro_names if not name.endswith("_H")]
    if not macro_names:
        errors.append(_violation("ETFW306", path, "no ET_CHIP_* mapping contract was found"))
        return errors

    invalid_names = [
        name for name in macro_names if not name.endswith(_CHIP_CONFIG_ALLOWED_SUFFIXES)
    ]
    for name in invalid_names:
        errors.append(_violation("ETFW307", path, f"unsupported Chip Config macro shape: {name}"))

    public_contracts = [
        name for name in macro_names if name.endswith(("_MAP_TABLE", "_STATUS_MASKS"))
    ]
    for name in public_contracts:
        count = wrap_sources.count(name)
        if count != 1:
            errors.append(
                _violation(
                    "ETFW308",
                    path,
                    f"{name} must have exactly one common Wrap consumer; found {count}",
                )
            )

    local_aggregates = [
        name for name in macro_names if name.endswith(("_FEATURE_FLAGS", "_LIMITS"))
    ]
    for name in local_aggregates:
        if source.count(name) <= 1:
            errors.append(
                _violation("ETFW309", path, f"unused or one-use aggregate is forbidden: {name}")
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check firmware Service and Wrap architecture rules."
    )
    parser.add_argument("root", type=Path, nargs="?", default=Path.cwd())
    args = parser.parse_args()
    service_root = args.root / "firmware/services/src"
    wrap_root = args.root / "firmware/wrap/src"
    chip_root = args.root / "firmware/chips"
    service_paths = [
        *sorted(service_root.glob("et_*_service.c")),
        *sorted((args.root / "firmware/services/include").glob("et_*_service.h")),
    ]
    errors = [error for path in service_paths for error in check_file(path)]
    errors.extend(error for path in service_paths for error in check_service_factory_contract(path))
    errors.extend(
        error
        for path in sorted(wrap_root.glob("et_*_wrap.c"))
        for error in check_wrap_driver_boundary(path)
    )
    config_paths = sorted(chip_root.glob(f"*/config/{_CHIP_CONFIG_NAME}"))
    if not config_paths:
        errors.append(
            _violation("ETFW310", chip_root, f"no */config/{_CHIP_CONFIG_NAME} file found")
        )
    for path in config_paths:
        errors.extend(check_chip_wrap_config(path, wrap_root))
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
