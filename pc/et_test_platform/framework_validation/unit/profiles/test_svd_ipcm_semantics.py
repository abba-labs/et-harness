# Mailbox能力生成合同测试。
# 职责：验证完整寄存器形状、容量交叉核对和重命名后的确定性。
# 边界：不操作硬件，不把测试执行环境提升为硅能力。
# 依赖：仅依赖SVD生成器、目标SVD和不可变事实替换。

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from .test_svd_capability_generator import _load_generator

CODE_ROOT = Path(__file__).parents[5]
SVD_PATH = CODE_ROOT / "test_case_doc" / "ET6801.svd"


# 仅解析一次目标SVD，各测试只替换独立的不可变Mailbox事实。
@pytest.fixture(scope="module")
def mailbox_facts():

    generator = _load_generator()
    facts = generator.parse_svd_facts(SVD_PATH)
    group = next(group for group in facts.groups if group.ip_id == "ipcm")
    return generator, replace(facts, groups=(group,))


# 正向：旧版本基线与当前生成器的全部语义/证据一致，只允许工具版本元数据递增。
def test_mailbox_profile_matches_generated_and_quality(mailbox_facts):

    generator, facts = mailbox_facts
    artifacts, profiles, audits = generator.build_semantic_documents(svd_path=SVD_PATH, facts=facts)
    repeated = generator.build_semantic_documents(svd_path=SVD_PATH, facts=facts)
    assert (profiles, audits) == repeated[1:]
    actual = CODE_ROOT / "pc/et_test_platform/profiles/chip_capabilities/et6801/ip/ipcm.yaml"
    baseline = yaml.safe_load(actual.read_text(encoding="utf-8"))
    generated = yaml.safe_load(profiles["ipcm"])
    assert baseline["source"]["generator_version"] <= generated["source"]["generator_version"]
    baseline["source"]["generator_version"] = generated["source"]["generator_version"]
    assert baseline == generated
    quality, _ = generator.build_quality_document(artifacts, facts=facts)
    assert quality["status"] == "pass", quality["issues"]
    capabilities = artifacts.profiles["ipcm"]["capabilities"]
    assert len(capabilities["features"]) == 9
    assert capabilities["limits"]["mailbox_count"] == {"ipcm0": 16}
    assert capabilities["limits"]["payload_bytes_per_mailbox"] == {"ipcm0": 28}
    assert capabilities["limits"]["linked_payload_max_bytes"] == {"ipcm0": 448}
    assert capabilities["options"]["ack_modes"]["ipcm0"] == ("manual", "auto")


# 通用性：改芯片/IP/实例/外设名和基址后，同一形状仍得到相同语义。
def test_mailbox_semantics_do_not_depend_on_chip_name_or_address(mailbox_facts):

    generator, facts = mailbox_facts
    group = facts.groups[0]
    instance = group.instances[0]
    instance = replace(
        instance,
        instance_id="message7",
        peripheral=replace(instance.peripheral, svd_name="MESSAGE_UNIT", base_address=0x60000000),
    )
    renamed = replace(
        facts,
        device_name="OTHER_CHIP",
        groups=(replace(group, ip_id="message", instances=(instance,)),),
    )
    artifacts, _, _ = generator.build_semantic_documents(svd_path=SVD_PATH, facts=renamed)
    capabilities = artifacts.profiles["message"]["capabilities"]
    assert capabilities["features"]["auto_ack_link"] == ["message7"]
    assert capabilities["limits"]["mailbox_count"] == {"message7": 16}


# 反向：容量不一致、字段缺失、错误访问属性或保留编码均不得被猜成受支持。
@pytest.mark.parametrize(
    "mutation",
    ("capacity", "missing_data", "send_encoding", "overlap", "readonly_control", "reset_mask"),
)
def test_mailbox_incomplete_contract_is_not_promoted(mailbox_facts, mutation):

    generator, facts = mailbox_facts
    group = facts.groups[0]
    instance = group.instances[0]
    registers = []
    for register in instance.peripheral.registers:
        fields = list(register.fields)
        names = {field.name.upper() for field in fields}
        if "MAILBOXES" in names:
            if mutation == "capacity":
                register = replace(register, reset_value=register.reset_value ^ (1 << 16))
            if mutation == "reset_mask":
                register = replace(register, reset_mask=0)
        if mutation == "missing_data":
            fields = [field for field in fields if field.name.upper() != "DATA6"]
        if mutation == "send_encoding":
            fields = [
                replace(field, description="Unspecified command encoding")
                if field.name.upper() == "SEND"
                else field
                for field in fields
            ]
        if mutation == "overlap":
            fields = [
                replace(field, bit_offset=0) if field.name.upper() == "AUTOLINK" else field
                for field in fields
            ]
        if mutation == "readonly_control":
            fields = [
                replace(field, access="read-only") if field.name.upper() == "MASKCLEAR" else field
                for field in fields
            ]
        registers.append(replace(register, fields=tuple(fields)))
    instance = replace(
        instance, peripheral=replace(instance.peripheral, registers=tuple(registers))
    )
    changed = replace(facts, groups=(replace(group, instances=(instance,)),))
    artifacts, _, _ = generator.build_semantic_documents(svd_path=SVD_PATH, facts=changed)
    assert "auto_ack_link" not in artifacts.profiles["ipcm"]["capabilities"]["features"]
    assert "mailbox_count" not in artifacts.profiles["ipcm"]["capabilities"]["limits"]
