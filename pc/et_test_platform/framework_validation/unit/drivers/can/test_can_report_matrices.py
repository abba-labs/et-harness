# CAN多参数人工报告闭合回归。
# 职责：组合真实Case软件向量的Canonical结果，校验参数聚合及Excel上限。
# 边界：不改写硬件Artifact，不把软件Peer数据当HIL结论。
# 依赖：既有严格Case向量、公共Result模型和项目报告导出器。

import importlib.util
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

import pytest
from et_test_platform.framework_validation.unit.drivers.can import (
    test_can_rate_case as rates,
)
from et_test_platform.framework_validation.unit.drivers.can import (
    test_can_tdc_case as tdc,
)
from et_test_platform.framework_validation.unit.drivers.can import (
    test_can_timestamp_case as timestamps,
)
from et_test_platform.results.case_report import build_case_report_model
from et_test_platform.results.recorder import write_json_result


# 逐个执行真实Case后组合全部参数；不同时间戳读回不能被默认same聚合隐藏。
@pytest.mark.parametrize("matrix", ("rates", "tdc", "timestamps"))
def test_can_full_parameter_report(matrix, tmp_path, monkeypatch):
    if matrix == "rates":
        nodes = rates.NODES
    elif matrix == "tdc":
        nodes = (2_000_000, 5_000_000)
    else:
        nodes = (1, 2, 16)
    combined = tmp_path / "combined"
    case_id = ""
    for index, node in enumerate(nodes):
        output = tmp_path / f"node-{index}"
        if matrix == "rates":
            rates.test_rate_matrix_vectors(*node, None, output)
        elif matrix == "tdc":
            tdc.test_tdc_case_independent_wire_and_peer(node, None, output)
        else:
            timestamps.test_timestamp_case_vectors(node, None, monkeypatch, output)
        result = json.loads((output / "cases/node/result.json").read_text(encoding="utf-8"))
        result["case_run_id"] = f"node-{index}"
        result["parameter_id"] = str(node)
        case_id = result["case_id"]
        write_json_result(combined / f"cases/node-{index}/result.json", result)
    session = json.loads((output / "session.json").read_text(encoding="utf-8"))
    write_json_result(combined / "session.json", session)
    document = Path(__file__).resolve().parents[6] / "test_case_doc/can/can.md"
    model = build_case_report_model(document, combined)
    row = next(row for row in model["cases"] if row["case_id"] == case_id)
    assert row["status"] == "PASS"
    xlsx = tmp_path / "software-matrix.xlsx"
    script = document.parents[2] / "tools/reporting/generate_case_report.py"
    spec = importlib.util.spec_from_file_location("_can_matrix_export", script)
    assert spec is not None and spec.loader is not None
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    exporter._write_xlsx(model, xlsx)
    with ZipFile(xlsx) as archive:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        values = ["".join(item.itertext()) for item in root]
        assert case_id in values
        assert all(len(value) < 32767 for value in values if isinstance(value, str))
