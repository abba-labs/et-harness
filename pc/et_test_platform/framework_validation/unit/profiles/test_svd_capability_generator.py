# Framework Validation测试模块。
#
# 职责：验证test_svd_capability_generator 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from et_test_platform.profiles.capabilities import (
    load_capability_audit,
    load_capability_profile,
)

CODE_ROOT = Path(__file__).parents[5]
GENERATOR_PATH = CODE_ROOT / "tools" / "capabilities" / "generate_capabilities.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "et_svd_capability_generator",
        GENERATOR_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_synthetic_svd(path: Path) -> None:
    path.write_text(
        """<?xml version="1.0"?>
<device schemaVersion="1.1">
  <name>ET_TEST</name>
  <description>Synthetic device description.</description>
  <size>32</size>
  <access>read-write</access>
  <resetValue>0</resetValue>
  <resetMask>0xFFFFFFFF</resetMask>
  <peripherals>
    <peripheral>
      <name>FOO0</name>
      <description>Primary synthetic peripheral.</description>
      <baseAddress>0x40000000</baseAddress>
      <registers>
        <register>
          <name>CTRL</name>
          <description>Control register.</description>
          <addressOffset>0</addressOffset>
          <fields>
            <field>
              <name>FIFO_EN</name>
              <description>Enable the block.</description>
              <bitOffset>0</bitOffset>
              <bitWidth>1</bitWidth>
            </field>
            <field>
              <name>DS_UPD_EN</name>
              <description>Destination Status Update Enable.</description>
              <bitOffset>3</bitOffset>
              <bitWidth>1</bitWidth>
            </field>
            <field>
              <name>DE_ENABLE</name>
              <description>The 'DE Enable' register bit controls a signal.</description>
              <bitOffset>4</bitOffset>
              <bitWidth>1</bitWidth>
            </field>
            <field>
              <name>FC</name>
              <description>Values:</description>
              <bitOffset>5</bitOffset>
              <bitWidth>1</bitWidth>
              <enumeratedValues>
                <enumeratedValue>
                  <name>FC_SOURCE</name>
                  <description>Flow controller is source.</description>
                  <value>0</value>
                </enumeratedValue>
                <enumeratedValue>
                  <name>FC_DESTINATION</name>
                  <description>Flow controller is destination.</description>
                  <value>1</value>
                </enumeratedValue>
              </enumeratedValues>
            </field>
            <field>
              <name>MODE</name>
              <description>Select mode.Values: 0x0 (MODE_A): first mode0x1 (MODE_B): second mode</description>
              <bitRange>[2:1]</bitRange>
              <enumeratedValues>
                <enumeratedValue>
                  <name>MODE_A</name>
                  <description>Standard enum A.</description>
                  <value>0</value>
                </enumeratedValue>
                <enumeratedValue>
                  <name>MODE_B</name>
                  <description>Standard enum B.</description>
                  <value>1</value>
                </enumeratedValue>
                <enumeratedValue>
                  <name>MODE_DEFAULT</name>
                  <description>Default enum entry.</description>
                  <isDefault>true</isDefault>
                </enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
        <register>
          <dim>2</dim>
          <dimIncrement>4</dimIncrement>
          <name>DATA[%s]</name>
          <description>Array register.</description>
          <addressOffset>0x10</addressOffset>
          <fields>
            <field>
              <name>VALUE</name>
              <lsb>0</lsb>
              <msb>7</msb>
            </field>
          </fields>
        </register>
        <register>
          <name>CTRL_ALIAS</name>
          <description>Same-address alias.</description>
          <addressOffset>0</addressOffset>
        </register>
        <cluster>
          <dim>2</dim>
          <dimIncrement>0x10</dimIncrement>
          <name>CH[%s]</name>
          <description>Channel cluster.</description>
          <addressOffset>0x20</addressOffset>
          <register>
            <name>STATE</name>
            <description>Channel state.</description>
            <addressOffset>0</addressOffset>
          </register>
        </cluster>
      </registers>
      <interrupt>
        <name>FOO0_DONE</name>
        <description>Primary completion interrupt.</description>
        <value>10</value>
      </interrupt>
      <interrupt>
        <name>FOO0_0</name>
        <description>Primary numbered interrupt line.</description>
        <value>12</value>
      </interrupt>
    </peripheral>
    <peripheral derivedFrom="FOO0">
      <name>FOO1</name>
      <baseAddress>0x40001000</baseAddress>
      <interrupt>
        <name>FOO1_DONE</name>
        <description>Secondary completion interrupt.</description>
        <value>11</value>
      </interrupt>
    </peripheral>
  </peripherals>
</device>
""",
        encoding="utf-8",
        newline="\n",
    )


def test_one_generic_generator_expands_and_loads_all_instances(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    output_dir = tmp_path / "capabilities"
    _write_synthetic_svd(svd_path)

    profiles = generator.build_profiles(
        svd_path=svd_path,
        output_dir=output_dir,
    )
    assert tuple(profiles) == ("foo",)

    summary = generator.write_or_check_profiles(
        profiles,
        output_dir,
        check=False,
    )
    assert summary["profile_count"] == 1

    profile = load_capability_profile(output_dir / "foo.yaml")
    assert profile.chip_id == "et_test"
    assert profile.instances == ("foo0", "foo1")
    assert profile.supports("foo.feature.field.fifo_en", instance="foo0")
    assert profile.supports("foo.feature.field.value", instance="foo1")
    assert profile.supports(
        "foo.feature.interrupt.done",
        instance="foo1",
    )
    assert (
        profile.value(
            "foo.limit.instance_count",
            instance="foo0",
        )
        == 2
    )
    assert (
        profile.value(
            "foo.limit.register_count",
            instance="foo1",
        )
        == 6
    )
    assert (
        profile.value(
            "foo.limit.field.value.bit_width",
            instance="foo0",
        )
        == 8
    )
    assert profile.value(
        "foo.option.field.mode.encoded_values",
        instance="foo1",
    ) == (0, 1)
    assert (
        profile.value(
            "foo.identity.base_address",
            instance="foo1",
        )
        == "0x40001000"
    )


def test_generation_is_byte_deterministic_and_check_fails_closed(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    output_dir = tmp_path / "capabilities"
    _write_synthetic_svd(svd_path)

    first = generator.build_profiles(
        svd_path=svd_path,
        output_dir=output_dir,
    )
    generator.write_or_check_profiles(first, output_dir, check=False)
    first_bytes = (output_dir / "foo.yaml").read_bytes()

    second = generator.build_profiles(
        svd_path=svd_path,
        output_dir=output_dir,
    )
    generator.write_or_check_profiles(second, output_dir, check=True)
    assert (output_dir / "foo.yaml").read_bytes() == first_bytes

    (output_dir / "foo.yaml").write_bytes(first_bytes.replace(b"\n", b"\r\n"))
    with pytest.raises(generator.GenerationError, match="stale"):
        generator.write_or_check_profiles(
            second,
            output_dir,
            check=True,
        )

    (output_dir / "foo.yaml").write_bytes(first_bytes)
    (output_dir / "foo.yaml").write_text(
        (output_dir / "foo.yaml").read_text(encoding="utf-8") + "# stale\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(generator.GenerationError, match="stale"):
        generator.write_or_check_profiles(
            second,
            output_dir,
            check=True,
        )


def test_fact_ir_preserves_descriptions_enums_paths_and_provenance(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    _write_synthetic_svd(svd_path)

    first = generator.build_fact_document(svd_path=svd_path)
    second = generator.build_fact_document(svd_path=svd_path)
    assert second == first

    document = json.loads(first)
    assert document["schema"] == "et-svd-facts/v1"
    assert document["chip"] == "et_test"
    assert document["device"] == {
        "description": "Synthetic device description.",
        "svd_name": "ET_TEST",
    }
    assert document["source"]["file"] == "ET_TEST.svd"
    assert len(document["source"]["sha256"]) == 64

    foo0 = document["ips"]["foo"]["instances"]["foo0"]
    foo1 = document["ips"]["foo"]["instances"]["foo1"]
    assert foo0["description"] == "Primary synthetic peripheral."
    assert foo1["description"] == "Primary synthetic peripheral."
    assert foo1["derived_from"] == "FOO0"

    registers = {item["path"]: item for item in foo0["registers"]}
    assert tuple(registers) == (
        "FOO0.CTRL",
        "FOO0.CTRL_ALIAS",
        "FOO0.DATA[0]",
        "FOO0.DATA[1]",
        "FOO0.CH[0].STATE",
        "FOO0.CH[1].STATE",
    )
    assert registers["FOO0.CTRL"]["absolute_address"] == 0x40000000
    assert registers["FOO0.CTRL_ALIAS"]["absolute_address"] == 0x40000000
    assert registers["FOO0.DATA[1]"]["source_name"] == "DATA[%s]"
    assert registers["FOO0.DATA[1]"]["dim_index"] == "1"
    assert foo0["clusters"] == [
        {
            "path": "FOO0.CH[0]",
            "source_name": "CH[%s]",
            "dim_index": "0",
            "description": "Channel cluster.",
            "address_offset": 0x20,
            "absolute_address": 0x40000020,
            "size": 32,
            "access": "read-write",
            "reset_value": 0,
            "reset_mask": 0xFFFFFFFF,
        },
        {
            "path": "FOO0.CH[1]",
            "source_name": "CH[%s]",
            "dim_index": "1",
            "description": "Channel cluster.",
            "address_offset": 0x30,
            "absolute_address": 0x40000030,
            "size": 32,
            "access": "read-write",
            "reset_value": 0,
            "reset_mask": 0xFFFFFFFF,
        },
    ]

    fields = {item["name"]: item for item in registers["FOO0.CTRL"]["fields"]}
    mode = fields["MODE"]
    assert mode["path"] == "FOO0.CTRL.MODE"
    assert mode["description"].startswith("Select mode.Values:")
    assert mode["inline_values_text"].startswith("0x0 (MODE_A)")
    assert mode["inline_values"] == [
        {"name": "MODE_A", "value": 0, "description": "first mode"},
        {"name": "MODE_B", "value": 1, "description": "second mode"},
    ]
    assert mode["enumerated_values"][-1] == {
        "name": "MODE_DEFAULT",
        "value": None,
        "description": "Default enum entry.",
        "is_default": True,
    }
    assert foo1["registers"][0]["path"].startswith("FOO1.")
    assert foo1["interrupts"] == [
        {
            "path": "FOO1.interrupt.FOO1_DONE",
            "name": "FOO1_DONE",
            "description": "Secondary completion interrupt.",
            "irqn": 11,
        }
    ]


def test_fact_ir_cli_supports_atomic_generate_and_check(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    facts_path = tmp_path / "facts" / "et_test.json"
    _write_synthetic_svd(svd_path)

    assert (
        generator.main(
            [
                "--svd",
                str(svd_path),
                "--facts-output",
                str(facts_path),
                "--facts-only",
            ]
        )
        == 0
    )
    first = facts_path.read_bytes()
    assert (
        generator.main(
            [
                "--svd",
                str(svd_path),
                "--facts-output",
                str(facts_path),
                "--facts-only",
                "--check",
            ]
        )
        == 0
    )
    assert facts_path.read_bytes() == first

    facts_path.write_bytes(first + b" ")
    assert (
        generator.main(
            [
                "--svd",
                str(svd_path),
                "--facts-output",
                str(facts_path),
                "--facts-only",
                "--check",
            ]
        )
        == 2
    )


def test_fact_ir_disambiguates_same_name_at_different_offsets(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    _write_synthetic_svd(svd_path)
    text = svd_path.read_text(encoding="utf-8")
    duplicate = """
        <register>
          <name>CTRL</name>
          <addressOffset>0x80</addressOffset>
        </register>
"""
    svd_path.write_text(
        text.replace("      </registers>", duplicate + "      </registers>", 1),
        encoding="utf-8",
        newline="\n",
    )

    document = json.loads(generator.build_fact_document(svd_path=svd_path))
    registers = document["ips"]["foo"]["instances"]["foo0"]["registers"]
    paths = {item["path"] for item in registers}
    assert "FOO0.CTRL@0x00000000" in paths
    assert "FOO0.CTRL@0x00000080" in paths


def test_fact_ir_rejects_same_name_at_same_offset(tmp_path: Path) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    _write_synthetic_svd(svd_path)
    text = svd_path.read_text(encoding="utf-8")
    duplicate = """
        <register>
          <name>CTRL</name>
          <addressOffset>0</addressOffset>
        </register>
"""
    svd_path.write_text(
        text.replace("      </registers>", duplicate + "      </registers>", 1),
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(generator.GenerationError, match="logical path"):
        generator.build_fact_document(svd_path=svd_path)


def test_fact_ir_cli_requires_explicit_fact_output(tmp_path: Path) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    _write_synthetic_svd(svd_path)
    assert generator.main(["--svd", str(svd_path), "--facts-only"]) == 2


def test_semantic_stage_emits_v2_audit_and_explain(tmp_path: Path) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    semantic_dir = tmp_path / "semantic"
    audit_dir = tmp_path / "audit"
    _write_synthetic_svd(svd_path)

    facts = generator.parse_svd_facts(svd_path)
    artifacts, profiles, audits = generator.build_semantic_documents(
        svd_path=svd_path,
        facts=facts,
    )
    generator.write_or_check_profiles(profiles, semantic_dir, check=False)
    generator.write_or_check_profiles(audits, audit_dir, check=False)

    profile = load_capability_profile(semantic_dir / "foo.yaml")
    assert profile.schema == "et-ip-capability/v2"
    assert profile.has_feature("fifo", instance="foo0")
    assert profile.has_feature("fifo", instance="foo1")
    assert profile.has_feature(
        "destination_status_update",
        instance="foo0",
    )
    assert "foo.feature.de" not in profile.capability_ids
    assert profile.options("mode", instance="foo0") == (
        "mode_a",
        "mode_b",
    )
    assert profile.options("flow_controller", instance="foo0") == (
        "source",
        "destination",
    )
    assert profile.interrupt("done", instance="foo1").svd_name == "FOO1_DONE"
    assert profile.interrupt("done", instance="foo1").irqn == 11
    assert profile.interrupt("line_0", instance="foo0").irqn == 12
    assert profile.identity("base_address", instance="foo1") == "0x40001000"
    evidence = profile.evidence("option", "mode", instance="foo0")
    assert evidence[0].path == "FOO0.CTRL.MODE"
    assert evidence[0].rule == "enumerated_values"

    audit = load_capability_audit(audit_dir / "foo.yaml")
    unclassified = {
        (item.instance, item.kind, item.path, item.reason) for item in audit.unclassified
    }
    assert (
        "foo0",
        "field",
        "FOO0.DATA[0].VALUE",
        "no_semantic_mapping",
    ) in unclassified
    assert (
        "foo0",
        "register",
        "FOO0.CTRL_ALIAS",
        "no_fields",
    ) in unclassified
    assert (
        "foo0",
        "field",
        "FOO0.CTRL.DE_ENABLE",
        "no_semantic_mapping",
    ) in unclassified

    explanation = generator.explain_semantic(
        artifacts,
        "foo.interrupt.done",
    )
    assert explanation["value"]["foo0"] == {
        "svd_name": "FOO0_DONE",
        "irqn": 10,
    }
    assert explanation["evidence"][0] == {
        "instance": "foo0",
        "kind": "interrupt",
        "path": "FOO0.interrupt.FOO0_DONE",
        "rule": "direct",
    }

    generator.write_or_check_profiles(profiles, semantic_dir, check=True)
    generator.write_or_check_profiles(audits, audit_dir, check=True)

    quality, quality_text = generator.build_quality_document(
        artifacts,
        facts=facts,
        required_capabilities=("foo.interrupt.done",),
    )
    assert json.loads(quality_text) == quality
    assert quality["schema"] == "et-capability-quality/v1"
    assert quality["status"] == "pass"
    assert quality["summary"]["profiles"] == 1
    assert quality["summary"]["instances"] == 2
    assert quality["summary"]["classified_facts"] > 0
    assert quality["summary"]["unclassified_facts"] > 0
    assert quality["summary"]["warnings"] == 0
    assert quality["per_ip"]["foo"]["audit_reason_counts"] == {
        "no_fields": 6,
        "no_semantic_mapping": 6,
    }
    assert quality["per_ip"]["foo"]["semantic_candidate_group_counts"] == {
        "feature": 1,
    }
    assert quality["per_ip"]["foo"]["semantic_candidate_fact_counts"] == {
        "feature": 2,
    }
    assert quality["summary"]["semantic_candidate_groups"] == 1
    assert quality["summary"]["semantic_candidate_facts"] == 2
    assert quality["per_ip"]["foo"]["semantic_candidate_groups"] == [
        {
            "kind": "feature",
            "rule": "boolean_enable_field",
            "reason": "no_semantic_mapping",
            "access": "read-write",
            "path_pattern": "ctrl.de_enable",
            "occurrence_count": 2,
            "instances": ["foo0", "foo1"],
            "source_names": ["DE_ENABLE"],
            "example_paths": [
                "FOO0.CTRL.DE_ENABLE",
                "FOO1.CTRL.DE_ENABLE",
            ],
        },
    ]
    assert "foo.feature.destination_status_update" in (quality["per_ip"]["foo"]["capability_ids"])
    assert quality["required_capabilities"] == [
        {
            "capability": "foo.interrupt.done",
            "present": True,
            "evidence_count": 2,
            "reason": "",
        }
    ]
    quality_path = tmp_path / "quality.json"
    generator.write_or_check_quality_document(
        quality_text,
        quality_path,
        check=False,
    )
    generator.write_or_check_quality_document(
        quality_text,
        quality_path,
        check=True,
    )


def test_quality_gate_fails_for_missing_required_capability(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    quality_path = tmp_path / "quality.json"
    _write_synthetic_svd(svd_path)

    facts = generator.parse_svd_facts(svd_path)
    artifacts, _, _ = generator.build_semantic_documents(
        svd_path=svd_path,
        facts=facts,
    )
    quality, _ = generator.build_quality_document(
        artifacts,
        facts=facts,
        required_capabilities=("foo.feature.missing",),
    )
    assert quality["status"] == "fail"
    assert quality["summary"]["errors"] == 1
    assert quality["issues"][0]["code"] == "required_capability_missing"

    assert (
        generator.main(
            [
                "--svd",
                str(svd_path),
                "--quality-output",
                str(quality_path),
                "--require-capability",
                "foo.feature.missing",
            ]
        )
        == 2
    )
    assert quality_path.is_file()


def test_capability_requirement_manifest_is_strict_and_canonical(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    manifest_path = tmp_path / "dma_p0.yaml"
    manifest_path.write_text(
        """schema: et-test-capability-requirements/v1
suite: dma_p0
required_capabilities:
  - foo.interrupt.done
  - foo.feature.destination_status_update
""",
        encoding="utf-8",
    )

    manifest = generator.load_capability_requirements(manifest_path)

    assert manifest.suite == "dma_p0"
    assert manifest.required_capabilities == (
        "foo.feature.destination_status_update",
        "foo.interrupt.done",
    )

    manifest_path.write_text(
        """schema: et-test-capability-requirements/v1
suite: dma_p0
required_capabilities:
  - foo.interrupt.done
  - foo.interrupt.done
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="repeats"):
        generator.load_capability_requirements(manifest_path)

    manifest_path.write_text(
        """schema: et-test-capability-requirements/v1
suite: dma_p0
required_capabilities:
  - foo.interrupt.done
""",
        encoding="utf-8",
    )
    first = generator.load_capability_requirements(manifest_path)
    with pytest.raises(ValueError, match="suite 'dma_p0' is repeated"):
        generator.merge_capability_requirements((first, first))


def test_cli_applies_requirement_manifest_to_quality_gate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    manifest_path = tmp_path / "foo_p0.yaml"
    quality_path = tmp_path / "quality.json"
    _write_synthetic_svd(svd_path)
    manifest_path.write_text(
        """schema: et-test-capability-requirements/v1
suite: foo_p0
required_capabilities:
  - foo.interrupt.done
""",
        encoding="utf-8",
    )

    assert (
        generator.main(
            [
                "--svd",
                str(svd_path),
                "--quality-output",
                str(quality_path),
                "--requirements-file",
                str(manifest_path),
                "--require-capability",
                "foo.feature.destination_status_update",
            ]
        )
        == 0
    )

    summary = json.loads(capsys.readouterr().out)
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    assert summary["requirement_suites"] == ["foo_p0"]
    assert [item["capability"] for item in quality["required_capabilities"]] == [
        "foo.feature.destination_status_update",
        "foo.interrupt.done",
    ]


def test_cli_requirement_manifest_fails_when_capability_is_missing(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    manifest_path = tmp_path / "foo_p0.yaml"
    _write_synthetic_svd(svd_path)
    manifest_path.write_text(
        """schema: et-test-capability-requirements/v1
suite: foo_p0
required_capabilities:
  - foo.feature.missing
""",
        encoding="utf-8",
    )

    assert (
        generator.main(
            [
                "--svd",
                str(svd_path),
                "--requirements-file",
                str(manifest_path),
            ]
        )
        == 2
    )


def test_classified_feature_is_not_repeated_as_ambiguous_audit(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    _write_synthetic_svd(svd_path)
    text = svd_path.read_text(encoding="utf-8")
    first_enums = """
              <enumeratedValues>
                <enumeratedValue><name>FIFO_DISABLED</name><value>0</value></enumeratedValue>
                <enumeratedValue><name>FIFO_ENABLED</name><value>1</value></enumeratedValue>
              </enumeratedValues>
"""
    text = text.replace(
        "              <bitWidth>1</bitWidth>\n            </field>",
        "              <bitWidth>1</bitWidth>" + first_enums + "            </field>",
        1,
    )
    second_register = """
        <register>
          <name>ALT</name>
          <addressOffset>8</addressOffset>
          <fields>
            <field>
              <name>FIFO_EN</name>
              <bitOffset>0</bitOffset>
              <bitWidth>1</bitWidth>
              <enumeratedValues>
                <enumeratedValue><name>FIFO_OFF</name><value>0</value></enumeratedValue>
                <enumeratedValue><name>FIFO_ON</name><value>1</value></enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
"""
    text = text.replace(
        "        <register>\n          <name>CTRL_ALIAS</name>",
        second_register + "        <register>\n          <name>CTRL_ALIAS</name>",
        1,
    )
    svd_path.write_text(text, encoding="utf-8", newline="\n")

    facts = generator.parse_svd_facts(svd_path)
    artifacts, _, _ = generator.build_semantic_documents(
        svd_path=svd_path,
        facts=facts,
    )
    profile = artifacts.profiles["foo"]
    audit = artifacts.audits["foo"]
    assert "fifo" in profile["capabilities"]["features"]
    assert "fifo" not in profile["capabilities"]["options"]
    assert "fifo_enable" not in profile["capabilities"]["options"]
    assert not any(item["path"].endswith(".FIFO_EN") for item in audit["unclassified"])
    quality, _ = generator.build_quality_document(artifacts, facts=facts)
    assert quality["status"] == "pass"
    assert not any(
        item["code"] == "semantic_fact_duplicate_name_classification" for item in quality["issues"]
    )


def test_quality_distinguishes_identity_only_profiles_with_explicit_markers(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    _write_synthetic_svd(svd_path)
    text = svd_path.read_text(encoding="utf-8")
    peripherals = """
    <peripheral>
      <name>BAR</name>
      <baseAddress>0x50000000</baseAddress>
      <registers>
        <register>
          <name>CTRL0</name>
          <addressOffset>0</addressOffset>
          <fields>
            <field>
              <name>ENABLE</name>
              <bitOffset>0</bitOffset>
              <bitWidth>1</bitWidth>
            </field>
            <field>
              <name>IC</name>
              <bitOffset>1</bitOffset>
              <bitWidth>2</bitWidth>
              <enumeratedValues>
                <enumeratedValue>
                  <name>IC_0</name>
                  <description>IC is 8 bits.</description>
                  <value>0</value>
                </enumeratedValue>
                <enumeratedValue>
                  <name>IC_1</name>
                  <description>IC is 16 bits.</description>
                  <value>1</value>
                </enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
        <register>
          <name>CTRL1</name>
          <addressOffset>4</addressOffset>
          <fields>
            <field>
              <name>IC</name>
              <bitOffset>1</bitOffset>
              <bitWidth>2</bitWidth>
              <enumeratedValues>
                <enumeratedValue>
                  <name>IC_0</name>
                  <description>IC is 8 bits.</description>
                  <value>0</value>
                </enumeratedValue>
                <enumeratedValue>
                  <name>IC_1</name>
                  <description>IC is 32 bits.</description>
                  <value>1</value>
                </enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
      </registers>
    </peripheral>
    <peripheral>
      <name>BAZ</name>
      <baseAddress>0x50001000</baseAddress>
      <registers>
        <register>
          <name>DATA</name>
          <addressOffset>0</addressOffset>
          <fields>
            <field>
              <name>VALUE</name>
              <bitOffset>0</bitOffset>
              <bitWidth>8</bitWidth>
            </field>
          </fields>
        </register>
      </registers>
    </peripheral>
"""
    text = text.replace("  </peripherals>", peripherals + "  </peripherals>")
    svd_path.write_text(text, encoding="utf-8", newline="\n")

    facts = generator.parse_svd_facts(svd_path)
    artifacts, _, _ = generator.build_semantic_documents(
        svd_path=svd_path,
        facts=facts,
    )
    quality, _ = generator.build_quality_document(artifacts, facts=facts)

    assert quality["per_ip"]["bar"]["identity_only_review"] == ("explicit_candidates_unresolved")
    assert quality["per_ip"]["bar"]["identity_only_surface"] == "writable"
    assert quality["per_ip"]["bar"]["semantic_candidate_group_counts"] == {
        "feature": 1,
        "limit": 2,
        "option": 2,
    }
    assert quality["summary"]["semantic_candidate_conflicts"] == 2
    assert {
        (item["kind"], item["path_pattern"], item["access"])
        for item in quality["per_ip"]["bar"]["semantic_candidate_value_conflicts"]
    } == {
        ("limit", "ctrl#.ic", "read-write"),
        ("option", "ctrl#.ic", "read-write"),
    }
    assert quality["per_ip"]["baz"]["identity_only_review"] == ("no_explicit_candidates")
    assert quality["per_ip"]["baz"]["identity_only_surface"] == "writable"
    assert {(item["code"], item.get("ip")) for item in quality["issues"]} >= {
        ("identity_only_with_explicit_candidates", "bar"),
        ("identity_only_without_explicit_candidates", "baz"),
        ("semantic_candidate_value_conflict", "bar"),
    }
    with pytest.raises(ValueError, match="different SVD hashes"):
        generator.build_quality_document(
            artifacts,
            facts=replace(facts, source_sha256="0" * 64),
        )


def test_semantic_options_require_read_write_access(tmp_path: Path) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    _write_synthetic_svd(svd_path)
    text = svd_path.read_text(encoding="utf-8")
    peripheral = """
    <peripheral>
      <name>ACCESS</name>
      <baseAddress>0x50002000</baseAddress>
      <registers>
        <register>
          <name>CONFIG</name>
          <addressOffset>0</addressOffset>
          <access>read-write</access>
          <fields>
            <field>
              <name>MODE</name>
              <bitOffset>0</bitOffset>
              <bitWidth>1</bitWidth>
              <enumeratedValues>
                <enumeratedValue><name>MODE_A</name><value>0</value></enumeratedValue>
                <enumeratedValue><name>MODE_B</name><value>1</value></enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
        <register>
          <name>STATUS</name>
          <addressOffset>4</addressOffset>
          <access>read-only</access>
          <fields>
            <field>
              <name>MODE</name>
              <bitOffset>0</bitOffset>
              <bitWidth>1</bitWidth>
              <enumeratedValues>
                <enumeratedValue><name>MODE_A</name><value>0</value></enumeratedValue>
                <enumeratedValue><name>MODE_B</name><value>1</value></enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
        <register>
          <name>COMMAND</name>
          <addressOffset>8</addressOffset>
          <access>write-only</access>
          <fields>
            <field>
              <name>MODE</name>
              <bitOffset>0</bitOffset>
              <bitWidth>1</bitWidth>
              <enumeratedValues>
                <enumeratedValue><name>MODE_A</name><value>0</value></enumeratedValue>
                <enumeratedValue><name>MODE_B</name><value>1</value></enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
        <register>
          <name>COMPONENT</name>
          <addressOffset>12</addressOffset>
          <access>read-only</access>
          <resetValue>5</resetValue>
          <fields>
            <field>
              <name>PRESENT_EN</name>
              <bitOffset>0</bitOffset>
              <bitWidth>1</bitWidth>
            </field>
            <field>
              <name>ABSENT_EN</name>
              <bitOffset>1</bitOffset>
              <bitWidth>1</bitWidth>
            </field>
            <field>
              <name>CH0_PRESENT_EN</name>
              <bitOffset>2</bitOffset>
              <bitWidth>1</bitWidth>
              <enumeratedValues>
                <enumeratedValue><name>FALSE</name><value>0</value></enumeratedValue>
                <enumeratedValue><name>TRUE</name><value>1</value></enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
        <register>
          <name>COUNTER_CONTROL</name>
          <addressOffset>16</addressOffset>
          <access>read-write</access>
          <fields>
            <field>
              <name>ENABLE</name>
              <description>Counter enable</description>
              <bitOffset>0</bitOffset>
              <bitWidth>1</bitWidth>
            </field>
          </fields>
        </register>
        <register>
          <name>ENGINE_CONTROL</name>
          <addressOffset>20</addressOffset>
          <access>read-write</access>
          <fields>
            <field>
              <name>EN</name>
              <description>Enables the engine.</description>
              <bitOffset>0</bitOffset>
              <bitWidth>1</bitWidth>
              <enumeratedValues>
                <enumeratedValue>
                  <name>DISABLED</name>
                  <value>0</value>
                </enumeratedValue>
                <enumeratedValue>
                  <name>ENABLED</name>
                  <value>1</value>
                </enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
        <register>
          <name>TIMER_CONTROL</name>
          <addressOffset>24</addressOffset>
          <access>read-write</access>
          <fields>
            <field>
              <name>ENABLE</name>
              <description>1 The timer is enabled and running, 0 The timer is disabled and stopped</description>
              <bitOffset>0</bitOffset>
              <bitWidth>1</bitWidth>
            </field>
          </fields>
        </register>
        <register>
          <name>GENERIC_COMP_PARAMS_CH0</name>
          <description>Component Parameters for channel 0</description>
          <addressOffset>28</addressOffset>
          <access>read-only</access>
          <resetValue>5</resetValue>
          <fields>
            <field>
              <name>CH0_FIFO_DEPTH</name>
              <bitOffset>0</bitOffset>
              <bitWidth>2</bitWidth>
              <enumeratedValues>
                <enumeratedValue>
                  <name>FIFO_DEPTH_8</name>
                  <description>FIFO depth is 8 bytes</description>
                  <value>0</value>
                </enumeratedValue>
                <enumeratedValue>
                  <name>FIFO_DEPTH_16</name>
                  <description>FIFO depth is 16 bytes</description>
                  <value>1</value>
                </enumeratedValue>
              </enumeratedValues>
            </field>
            <field>
              <name>CH0_PRESENT_EN</name>
              <bitOffset>2</bitOffset>
              <bitWidth>1</bitWidth>
              <enumeratedValues>
                <enumeratedValue><name>FALSE</name><value>0</value></enumeratedValue>
                <enumeratedValue><name>TRUE</name><value>1</value></enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
        <register>
          <name>GENERIC_COMP_PARAMS_CH1</name>
          <description>Component Parameters for channel 1</description>
          <addressOffset>32</addressOffset>
          <access>read-only</access>
          <resetValue>5</resetValue>
          <fields>
            <field>
              <name>CH1_FIFO_DEPTH</name>
              <bitOffset>0</bitOffset>
              <bitWidth>2</bitWidth>
              <enumeratedValues>
                <enumeratedValue>
                  <name>IFO_DEPTH_8</name>
                  <description>FIFO depth is 8 bytes</description>
                  <value>0</value>
                </enumeratedValue>
                <enumeratedValue>
                  <name>FIFO_DEPTH_16</name>
                  <description>FIFO depth is 16 bytes</description>
                  <value>1</value>
                </enumeratedValue>
              </enumeratedValues>
            </field>
            <field>
              <name>CH1_PRESENT_EN</name>
              <bitOffset>2</bitOffset>
              <bitWidth>1</bitWidth>
              <enumeratedValues>
                <enumeratedValue><name>FALSE</name><value>0</value></enumeratedValue>
                <enumeratedValue><name>TRUE</name><value>1</value></enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
      </registers>
    </peripheral>
"""
    text = text.replace("  </peripherals>", peripheral + "  </peripherals>")
    svd_path.write_text(text, encoding="utf-8", newline="\n")

    facts = generator.parse_svd_facts(svd_path)
    artifacts, _, _ = generator.build_semantic_documents(
        svd_path=svd_path,
        facts=facts,
    )
    profile = artifacts.profiles["access"]
    assert profile["capabilities"]["options"] == {"mode": {"access0": ("mode_a", "mode_b")}}
    assert profile["capabilities"]["features"] == {
        "counter": ["access0"],
        "engine": ["access0"],
        "present": ["access0"],
        "timer": ["access0"],
    }
    assert profile["capabilities"]["parameters"] == {
        "fifo_depth": {"access0": {"channel_0": 16, "channel_1": 16}},
        "present": {"access0": {"channel_0": True, "channel_1": True}},
    }
    assert {
        (item["member"], item["path"])
        for item in profile["evidence"]["access.parameter.fifo_depth"]
    } == {
        (
            "channel_0",
            "ACCESS.GENERIC_COMP_PARAMS_CH0.CH0_FIFO_DEPTH",
        ),
        (
            "channel_1",
            "ACCESS.GENERIC_COMP_PARAMS_CH1.CH1_FIFO_DEPTH",
        ),
    }
    assert {
        (item["path"], item["reason"]) for item in artifacts.audits["access"]["unclassified"]
    } >= {
        ("ACCESS.STATUS.MODE", "no_semantic_mapping"),
        ("ACCESS.COMMAND.MODE", "no_semantic_mapping"),
        ("ACCESS.COMPONENT.ABSENT_EN", "disabled_component_parameter"),
    }

    quality, _ = generator.build_quality_document(artifacts, facts=facts)
    assert quality["status"] == "pass"
    assert quality["summary"]["parameter_domain_conflicts"] == 1
    assert {
        item.get("capability")
        for item in quality["issues"]
        if item["code"] == "component_parameter_domain_conflict"
    } == {"access.parameter.fifo_depth"}
    candidates = quality["per_ip"]["access"]["semantic_candidate_groups"]
    assert {
        (item["path_pattern"], item["access"]) for item in candidates if item["kind"] == "option"
    } == {
        ("command.mode", "write-only"),
        ("status.mode", "read-only"),
    }
    assert not any(
        item["code"]
        in {
            "disabled_readonly_feature_evidence",
            "non_configurable_value_capability",
            "semantic_fact_duplicate_name_classification",
            "cross_kind_name_collision",
        }
        for item in quality["issues"]
    )


def test_stable_vendor_and_cortex_tokens_are_not_short_name_warnings() -> None:
    _load_generator()
    from svd_semantics import opaque_short_tokens

    assert opaque_short_tokens("misc_m7") == ()
    assert opaque_short_tokens("et_head") == ()
    assert opaque_short_tokens("misc_xy") == ("xy",)


# 验证 ET6801 CRC 静态 Capability 已由 SVD 证据完整生成。
def test_et6801_crc_profile_contains_required_svd_semantics() -> None:
    profile = load_capability_profile(
        CODE_ROOT
        / "pc"
        / "et_test_platform"
        / "profiles"
        / "chip_capabilities"
        / "et6801"
        / "ip"
        / "crc.yaml"
    )

    assert profile.supports("crc.feature.module_enable", instance="crc0")
    assert profile.supports("crc.feature.polynomial", instance="crc0")
    assert profile.supports("crc.feature.irq_raw_status", instance="crc0")
    assert profile.value("crc.option.modes", instance="crc0") == (
        "crc8",
        "crc16",
        "crc32",
    )
    assert profile.value("crc.option.byte_swap_modes", instance="crc0") == (
        "crc16",
        "crc32",
    )
    assert profile.value("crc.option.irq_sources", instance="crc0") == (
        "bus_error",
        "length_error",
        "check_error",
    )
    assert profile.value("crc.limit.length_field_max", instance="crc0") == 65535
    assert profile.value("crc.limit.fifo_threshold_max", instance="crc0") == 8
    assert dict(profile.value("crc.parameter.result_width_bits", instance="crc0")) == {
        "crc8": 8,
        "crc16": 16,
        "crc32": 32,
    }


# 验证 ET6801 AES 能力由 SVD 语义生成，不依赖 Case 中的芯片硬编码。
def test_et6801_aes_profile_contains_required_svd_semantics() -> None:
    profile = load_capability_profile(
        CODE_ROOT
        / "pc"
        / "et_test_platform"
        / "profiles"
        / "chip_capabilities"
        / "et6801"
        / "ip"
        / "aes.yaml"
    )

    assert profile.supports("aes.feature.encryption", instance="aes0")
    assert profile.supports("aes.feature.decryption", instance="aes0")
    assert profile.supports("aes.feature.interrupts", instance="aes0")
    assert profile.supports("aes.feature.dma_fifo_path", instance="aes0")
    assert profile.value("aes.option.key_sizes", instance="aes0") == (128, 256)
    assert profile.value("aes.option.modes", instance="aes0") == ("ecb", "cbc", "ctr")
    assert profile.value("aes.option.padding_modes", instance="aes0") == (
        "none",
        "zero",
        "pkcs7",
    )
    assert profile.value("aes.limit.block_size_bytes", instance="aes0") == 16
    assert profile.value("aes.limit.data_length_bits", instance="aes0") == 36


# 验证 CORDIC 公共层依赖的模式、位宽、状态和中断能力均来自 SVD 语义。
def test_et6801_cordic_profile_contains_required_svd_semantics() -> None:
    profile = load_capability_profile(
        CODE_ROOT
        / "pc"
        / "et_test_platform"
        / "profiles"
        / "chip_capabilities"
        / "et6801"
        / "ip"
        / "cordic.yaml"
    )

    assert profile.supports("cordic.feature.calculation_engine", instance="cordic0")
    assert profile.supports("cordic.feature.interrupts", instance="cordic0")
    assert profile.value("cordic.option.math_functions", instance="cordic0") == (
        "sincos",
        "phase_modulus",
        "arctan",
        "hsincos",
        "atanh",
        "exp",
        "ln",
        "sqrt",
        "tan",
    )
    assert profile.value("cordic.option.numeric_modes", instance="cordic0") == (
        "fixed",
        "float32",
    )
    assert profile.value("cordic.option.argument_widths", instance="cordic0") == (16, 32)
    assert profile.value("cordic.option.result_widths", instance="cordic0") == (16, 32)
    assert profile.value("cordic.option.work_modes", instance="cordic0") == (
        "interrupt",
        "polling",
        "zero_overhead",
        "dma",
    )
    assert profile.value("cordic.option.irq_sources", instance="cordic0") == (
        "arg_overflow",
        "calculation_complete",
        "pm_arg2_error",
    )


def test_semantic_cli_requires_profile_and_audit_dirs_together(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    svd_path = tmp_path / "ET_TEST.svd"
    _write_synthetic_svd(svd_path)
    assert (
        generator.main(
            [
                "--svd",
                str(svd_path),
                "--semantic-output-dir",
                str(tmp_path / "semantic"),
            ]
        )
        == 2
    )

    assert (
        generator.main(
            [
                "--svd",
                str(svd_path),
                "--semantic-output-dir",
                str(tmp_path / "semantic"),
                "--audit-output-dir",
                str(tmp_path / "audit"),
                "--explain",
                "foo.interrupt.done",
                "--quality-output",
                str(tmp_path / "quality.json"),
                "--require-capability",
                "foo.interrupt.done",
            ]
        )
        == 0
    )
