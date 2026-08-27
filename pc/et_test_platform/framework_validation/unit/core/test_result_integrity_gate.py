# Framework Validation测试模块。
#
# 职责：验证test_result_integrity_gate 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path


# A logical PASS without required evidence must be unsuccessful everywhere.
def test_missing_required_evidence_fails_result_junit_and_process(tmp_path: Path) -> None:

    test_file = tmp_path / "test_missing_evidence.py"
    test_file.write_text(
        "import pytest\n"
        "class _Framework:\n"
        "    chip_id = 'et6801'\n"
        "    firmware_build_id = 'build-test'\n"
        "    registry_hash = 'deadbeef'\n"
        "    transport_identity = 'fake:serial'\n"
        "@pytest.fixture\n"
        "def framework_communication(record_property):\n"
        "    record_property('required_evidence_sources', ['dut'])\n"
        "    return _Framework()\n"
        "def test_logical_pass_without_evidence(framework_communication):\n"
        "    assert framework_communication.chip_id == 'et6801'\n",
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "artifacts"
    junit_path = tmp_path / "junit.xml"
    repository_root = Path(__file__).parents[5]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repository_root / "pc")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(test_file),
            "-p",
            "et_test_platform.pytest_plugin",
            "--et-artifact-dir",
            str(artifact_dir),
            "--junitxml",
            str(junit_path),
        ],
        cwd=repository_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0, completed.stdout + completed.stderr

    result_files = sorted((artifact_dir / "cases").glob("*/result.json"))
    assert len(result_files) == 1
    result = json.loads(result_files[0].read_text(encoding="utf-8"))
    assert result["status"] == "EVIDENCE_MISSING"
    assert result["missing_evidence_sources"] == ["dut"]
    assert "missing required evidence sources: dut" in result["error"]

    session = json.loads((artifact_dir / "session.json").read_text(encoding="utf-8"))
    assert session["exitstatus"] != 0
    assert session["status_counts"]["EVIDENCE_MISSING"] == 1

    root = ElementTree.parse(junit_path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    assert suites
    unsuccessful = sum(
        int(suite.attrib.get("failures", "0")) + int(suite.attrib.get("errors", "0"))
        for suite in suites
    )
    assert unsuccessful >= 1
