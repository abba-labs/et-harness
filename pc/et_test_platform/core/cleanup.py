# 清理错误聚合 的跨 IP 公共基础实现。
#
# 职责：提供芯片无关的清理错误聚合语义，供 Driver、Case 和通信层复用。
# 边界：不包含任何 IP Command、Wire 字段、Bench 事实或设备 I/O。
# 依赖：仅依赖 Python 标准库和 core 层内部稳定类型。

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import NoReturn

from .errors import EtPlatformError

CleanupAction = tuple[str, Callable[[], None]]


# 提供 CleanupFailure 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
@dataclass(frozen=True, slots=True)
class CleanupFailure:
    stage: str
    error: BaseException


# 同时保留主错误和一个或多个 Cleanup 错误。
class OperationCleanupError(EtPlatformError):
    def __init__(
        self,
        primary_error: BaseException,
        cleanup_failures: Iterable[CleanupFailure],
    ) -> None:
        failures = tuple(cleanup_failures)
        if not failures:
            raise ValueError("cleanup_failures must not be empty")
        self.primary_error = primary_error
        self.cleanup_failures = failures
        details = "; ".join(f"{failure.stage}: {failure.error}" for failure in failures)
        super().__init__(f"{primary_error}; cleanup failures: {details}")


# 按调用方给定顺序执行全部 Cleanup，并收集所有失败。
def run_cleanup(actions: Iterable[CleanupAction]) -> tuple[CleanupFailure, ...]:

    failures: list[CleanupFailure] = []
    for stage, action in actions:
        if not stage:
            raise ValueError("cleanup stage must not be empty")
        try:
            action()
        except BaseException as error:
            failures.append(CleanupFailure(stage=stage, error=error))
    return tuple(failures)


# 重新抛出主错误，或在 Cleanup 失败时抛出聚合异常。
def raise_with_cleanup(
    primary_error: BaseException,
    cleanup_failures: Iterable[CleanupFailure],
) -> NoReturn:

    failures = tuple(cleanup_failures)
    if failures:
        raise OperationCleanupError(primary_error, failures) from primary_error
    raise primary_error
