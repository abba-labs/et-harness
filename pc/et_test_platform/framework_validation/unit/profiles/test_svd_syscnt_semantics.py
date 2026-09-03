# 时间戳计数器能力生成回归。
# 职责：验证计数位宽、控制语义和窗口命名，缺字段时不得猜测能力。
# 边界：不连接硬件，不修改原始SVD和其他IP基线。
# 依赖：统一生成器、pytest及当前芯片SVD事实。

import importlib
import sys
from dataclasses import replace
from pathlib import Path

import pytest

CODE_ROOT = Path(__file__).parents[5]
sys.path.insert(0, str(CODE_ROOT / "tools" / "capabilities"))
generator = importlib.import_module("generate_capabilities")
GenerationError = generator.GenerationError
build_semantic_documents = generator.build_semantic_documents
parse_svd_facts = generator.parse_svd_facts
normalize = importlib.import_module("svd_semantics").normalize
analyze = importlib.import_module("capability_quality").analyze


# 使用当前芯片SVD验证真实字段描述，并独立验证另一个名称/基址不影响语义。
def test_timestamp_profile_has_one_logical_control_instance() -> None:
    facts = parse_svd_facts(CODE_ROOT / "test_case_doc" / "ET6801.svd")
    artifacts, profiles, _ = build_semantic_documents(
        svd_path=CODE_ROOT / "test_case_doc" / "ET6801.svd", facts=facts
    )
    profile = artifacts.profiles["syscnt"]
    assert set(profile["instances"]) == {"syscnt0"}
    assert profile["instances"]["syscnt0"]["svd_name"] == "SYSCNT_CTRL"
    assert profile["capabilities"]["limits"] == {
        "counter_bits": {"syscnt0": 64},
        "word_bits": {"syscnt0": 32},
    }
    assert set(profile["capabilities"]["features"]) == {"counter", "debug_halt", "frequency_id"}
    assert "SYSCNT_CTRL.CNTCR.HDBG" in profiles["syscnt"]
    assert not [
        issue for issue in analyze(artifacts, facts=facts)["issues"] if issue["severity"] == "error"
    ]

    group = next(group for group in facts.groups if group.ip_id == "syscnt")
    instance = group.instances[0]
    generic = replace(
        group,
        ip_id="timestamp",
        instances=(
            replace(
                instance,
                instance_id="timestamp0",
                peripheral=replace(
                    instance.peripheral, svd_name="TIMESTAMP_CTRL", base_address=0x41000000
                ),
            ),
        ),
    )
    renamed = normalize(replace(facts, groups=(generic,)), chip_id="synthetic")
    assert renamed.profiles["timestamp"]["capabilities"]["limits"]["counter_bits"] == {
        "timestamp0": 64
    }


# 高字缺失或说明不再证明时间戳上下字时，不宣称已知位宽或暂停能力。
@pytest.mark.parametrize("change", ("missing_upper", "ambiguous_description"))
def test_timestamp_shape_rejects_incomplete_facts(change: str) -> None:
    facts = parse_svd_facts(CODE_ROOT / "test_case_doc" / "ET6801.svd")
    group = next(group for group in facts.groups if group.ip_id == "syscnt")
    instance = group.instances[0]
    registers = []
    for register in instance.peripheral.registers:
        if register.path == "CNTCVU":
            if change == "missing_upper":
                continue
            register = replace(register, fields=(replace(register.fields[0], description="Value"),))
        registers.append(register)
    changed = replace(instance, peripheral=replace(instance.peripheral, registers=tuple(registers)))
    result = normalize(
        replace(facts, groups=(replace(group, instances=(changed,)),)), chip_id="synthetic"
    )
    assert "counter_bits" not in result.profiles["syscnt"]["capabilities"]["limits"]
    assert "debug_halt" not in result.profiles["syscnt"]["capabilities"]["features"]


# 仅名称完整成对时去除控制窗口后缀；已有同名外设时必须显式报歧义。
@pytest.mark.parametrize(
    "names,expected",
    (
        (("FOO_CTRL",), {"foo_ctrl"}),
        (("FOO_CTRL", "FOO_RO"), {"foo", "foo_ro"}),
    ),
)
def test_control_window_naming(tmp_path: Path, names: tuple[str, ...], expected: set[str]) -> None:
    source = tmp_path / "generic.svd"
    peripherals = "".join(
        f"<peripheral><name>{name}</name><baseAddress>0x40000000</baseAddress></peripheral>"
        for name in names
    )
    source.write_text(
        f"<device><name>GENERIC</name><peripherals>{peripherals}</peripherals></device>"
    )
    facts = parse_svd_facts(source)
    assert {group.ip_id for group in facts.groups} == expected
    if len(names) == 2:
        source.write_text(
            source.read_text().replace(
                "</peripherals>",
                "<peripheral><name>FOO</name><baseAddress>0x42000000</baseAddress></peripheral></peripherals>",
            )
        )
        with pytest.raises(GenerationError, match="ambiguous control-window"):
            parse_svd_facts(source)
