# 指定Pipeline身份的只读终态判断回归。
# 职责：拒绝旧Run、未终止状态和错误退出码的PASS。
# 边界：仅内存样本，不等待、不执行Pipeline或硬件。
# 依赖：pytest与监视入口。

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


# 测试方法：组合Run身份、终态与退出码；通过条件：只有当前Run明确成功返回0。
@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ({}, 0),
        ({"run_id": "previous-run"}, None),
        ({"schema": "unknown"}, None),
        ({"finished_at": None}, None),
        ({"finished_at": True}, None),
        ({"exit_code": False}, None),
        ({"exit_code": 1}, 1),
        ({"status": "FAIL"}, 1),
    ],
)
def test_terminal_result_is_bound_to_current_run(
    monkeypatch: pytest.MonkeyPatch,
    updates: dict[str, object],
    expected: int | None,
) -> None:
    repository = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repository / "tools/runner"))
    monitor = importlib.import_module("watch_pipeline_log")
    manifest = {
        "schema": "et-artifact-run/v1",
        "run_id": "current-run",
        "finished_at": "2026-09-12T09:00:00Z",
        "status": "PASS",
        "exit_code": 0,
        **updates,
    }
    assert monitor._terminal_result(manifest, "current-run") == expected
