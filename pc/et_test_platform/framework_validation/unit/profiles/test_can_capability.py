# CAN能力基线回归。
# 职责：核对审核后的ET6801 SVD身份、三实例基址和实例IRQ。
# 边界：不从这些事实推断尚未生成的Feature语义，不作为HIL证据。
# 依赖：仓库正式YAML和PyYAML。

import re
from pathlib import Path

import yaml

from et_test_platform import profiles
from et_test_platform.profiles.chip_execution_mappings.et6801 import can_routes


# 测试Feature：CAN DMA请求映射来自Own SYSCTRL SDK枚举，不把相邻IP编号猜成CAN编号。
# 测试方法：解析192起连续枚举，与三实例TX/RX独立Golden比较。
# 通过条件：表值、请求方向及32-bit传输宽度一致，变更SDK后映射漂移可见。
def test_can_dmu_requests_match_sdk_enum():
    root = Path(__file__).resolve().parents[5]
    header = (root / "firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_sysctrl.h").read_text(
        encoding="utf-8"
    )
    suffix = header.split("DMAMUX_REQ_UART0_TX = 192,", 1)[1].split("} SYSCTRL_DMAReqIdx", 1)[0]
    names = ["DMAMUX_REQ_UART0_TX", *re.findall(r"\bDMAMUX_REQ_\w+", suffix)]
    values = {name: value for value, name in enumerate(names, 192)}
    golden = {0: {"tx": 222, "rx": 223}, 1: {"tx": 224, "rx": 225}, 2: {"tx": 226, "rx": 227}}
    for instance, requests in golden.items():
        assert dict(can_routes.CAN_DMU_REQUESTS[instance]) == requests
        for direction, expected in requests.items():
            assert values[f"DMAMUX_REQ_CAN{instance}_{direction.upper()}"] == expected
    assert can_routes.CAN_DMU_WORD_BYTES == 4
    assert can_routes.CAN_DMU_ALLOWED_CONTROLLERS == (0, 1)
    assert tuple(range(8)) == can_routes.CAN_DMU_ALLOWED_INTERFACES


def test_can_capability_matches_reviewed_svd():
    path = Path(profiles.__file__).parent / "chip_capabilities/et6801/ip/can.yaml"
    profile = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert (
        profile["source"]["sha256"]
        == "49B2DE29BD7A0A4A5FBDEFC6E36D75CD6DA53A46F5504F860DEE53BE9079CCE4"
    )
    assert profile["source"]["generator_version"] == 11
    assert tuple(profile["instances"]) == ("can0", "can1", "can2")
    assert profile["capabilities"]["identities"]["base_address"] == {
        "can0": "0x4051C000",
        "can1": "0x40524000",
        "can2": "0x4052C000",
    }
    assert profile["capabilities"]["interrupts"]["int0"]["can0"]["irqn"] == 39
    assert profile["capabilities"]["features"] == {}
