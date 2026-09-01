# Pipeline Profile阶段依赖解析。
# 职责：把Operator选择展开为Profile声明的确定性前置阶段，并检测无效依赖。
# 边界：不读取配置文件、不执行阶段，也不判断硬件结果。

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


# 按依赖优先顺序展开选择；未知依赖、错误类型和依赖环必须失败关闭。
def resolve_step_dependencies(
    profile: Mapping[str, Any], selected_steps: Sequence[str]
) -> tuple[str, ...]:
    steps = profile.get("steps")
    if not isinstance(steps, Mapping):
        raise RuntimeError("pipeline profile steps must be a mapping")

    resolved: list[str] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(step: str) -> None:
        if step in visited:
            return
        if step in visiting:
            raise RuntimeError(f"pipeline profile step dependency cycle includes {step!r}")

        visiting.add(step)
        action = steps.get(step)
        if action is not None:
            if not isinstance(action, Mapping):
                raise RuntimeError(f"pipeline profile step {step!r} must be a mapping")
            dependencies = action.get("requires", [])
            if not isinstance(dependencies, list) or not all(
                isinstance(item, str) and item for item in dependencies
            ):
                raise RuntimeError(f"pipeline profile step {step!r} has invalid requires list")
            for dependency in dependencies:
                if dependency not in steps:
                    raise RuntimeError(
                        f"pipeline profile step {step!r} requires unknown step {dependency!r}"
                    )
                visit(dependency)

        visiting.remove(step)
        visited.add(step)
        resolved.append(step)

    for selected in selected_steps:
        visit(str(selected))

    return tuple(resolved)


__all__ = ["resolve_step_dependencies"]
