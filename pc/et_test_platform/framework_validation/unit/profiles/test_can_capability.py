# CAN能力基线回归。
# 职责：核对审核后的ET6801 SVD身份、三实例基址和实例IRQ。
# 边界：不从这些事实推断尚未生成的Feature语义，不作为HIL证据。
# 依赖：仓库正式YAML和PyYAML。

from pathlib import Path

import yaml

from et_test_platform import profiles


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
