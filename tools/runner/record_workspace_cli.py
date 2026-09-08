# PowerShell普通阶段复用现有固定现场校验的内部桥接入口。
# 职责：准备独立诊断current，或为成功且无Case的普通阶段登记完成回执。
# 边界：不运行测试，不确认Case知识，不接收任意删除范围。
# 依赖：已有record_workspace；仅由Artifact路径助手调用。

from __future__ import annotations

import argparse
from pathlib import Path

from record_workspace import prepare_workspace, seal_workspace


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal diagnostic workspace helper")
    parser.add_argument("operation", choices=("prepare", "complete"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    root = args.workspace.absolute()
    repository = args.repository.absolute()
    if root.parent.parent != repository / "artifacts/records/_DIAGNOSTICS":
        raise ValueError("internal helper only manages fixed diagnostic current workspaces")
    if args.operation == "prepare":
        prepare_workspace(repository, root)
    else:
        seal_workspace(repository, root, proofs={}, routine_success=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
