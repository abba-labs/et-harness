# CAN盒子连接配置适配。
# 职责：把Runner传入的基础连接字段转换成有类型的ZLG连接。
# 边界：不读取Case参数、不打开设备、不扫描DLL或其他工作树。
# 依赖：本包Adapter、标准库；本地路径由Run Config指定。

from collections.abc import Mapping
from pathlib import Path

from .zlg import ZlgCanBox, ZlgConnection


# CLI与Fixture共用同一解析入口；只接受显式声明的设备和通道。
def create_zlg_can_box(settings: Mapping[str, object], *, base: Path) -> ZlgCanBox:
    required = {"library", "device_type", "device_index", "channel", "termination"}
    unknown = set(settings) - required - {"kind", "serial"}
    if unknown or not required <= set(settings):
        raise ValueError(
            f"invalid CAN box connection keys: missing={required - set(settings)}, extra={unknown}"
        )
    if settings.get("kind", "usb") != "usb":
        raise ValueError("ZLG CAN box connection kind must be usb")
    library = settings["library"]
    device_type = settings["device_type"]
    serial = settings.get("serial", "")
    if not isinstance(library, str) or not library.strip():
        raise ValueError("CAN box library path is required")
    if not isinstance(device_type, str) or not isinstance(serial, str):
        raise ValueError("CAN box device_type and serial must be strings")
    # 相对路径只基于本机配置所在目录，不受启动命令的工作目录影响。
    path = Path(library)
    if not path.is_absolute():
        path = base / path
    return ZlgCanBox(
        ZlgConnection(
            path.resolve(),
            device_type,
            settings["device_index"],
            settings["channel"],
            settings["termination"],
            serial,
        )
    )


# Fixture读取Runner已经导出的设备字段；Case不直接读取run_config.yaml。
def create_zlg_can_box_from_environment(
    environment: Mapping[str, str], *, device_name: str, base: Path
) -> ZlgCanBox:
    prefix = f"ET_INSTRUMENT_{device_name.upper()}_"
    if environment.get(prefix + "DRIVER") != "zlg_can":
        raise ValueError(f"{device_name}: driver must be zlg_can")
    settings: dict[str, object] = {}
    for key in (
        "kind",
        "library",
        "device_type",
        "device_index",
        "channel",
        "termination",
        "serial",
    ):
        value = environment.get(prefix + key.upper())
        if value is not None:
            if key in ("device_index", "channel"):
                value = int(value)
            elif key == "termination":
                if value not in ("True", "False", "true", "false"):
                    raise ValueError("CAN box termination must be true/false")
                value = value.lower() == "true"
            settings[key] = value
    return create_zlg_can_box(settings, base=base)
