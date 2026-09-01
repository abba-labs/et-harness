# Framework Validation公共Fixture。
#
# 职责：为软件合同测试提供隔离的测试环境和共享事实。
# 边界：不执行未经门禁的真实硬件操作，也不改变生产语义。
# 依赖：仅依赖pytest和测试所需的本地工具。

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import PosixPath

import pytest


# Translate Keil separators only for the host path-existence contract.
@pytest.fixture(autouse=True)
def resolve_keil_windows_paths_on_posix(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:

    target_test = "test_generated_keil_project_uses_only_firmware_source_files"
    if os.name == "nt" or request.node.name != target_test:
        yield
        return

    original_join = PosixPath.__truediv__

    def portable_join(path: PosixPath, child: object) -> PosixPath:
        if isinstance(child, str):
            child = child.replace("\\", "/")
        return original_join(path, child)

    monkeypatch.setattr(PosixPath, "__truediv__", portable_join)
    yield
