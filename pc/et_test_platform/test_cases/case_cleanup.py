# Case跨IP清理聚合工具。
#
# 职责：按Case显式给出的顺序执行清理并保留主失败和清理失败。
# 边界：不决定资源所有权、不添加隐式清理，也不执行Feature流程。
# 依赖：仅依赖公共Cleanup模型。

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager

from ..core.cleanup import CleanupAction, OperationCleanupError, run_cleanup


# Execute every Case-owned cleanup action and preserve both failure sets.
#
# The Test Case constructs the named action list, so resource ownership and
# cleanup order remain visible in the Case body.  This helper only performs
# uniform aggregation.
@contextmanager
def case_cleanup_scope(
    actions_factory: Callable[[], Iterable[CleanupAction]],
) -> Iterator[None]:

    try:
        yield
    except BaseException as primary_error:
        failures = run_cleanup(tuple(actions_factory()))
        if failures:
            raise OperationCleanupError(primary_error, failures) from primary_error
        raise
    failures = run_cleanup(tuple(actions_factory()))
    if failures:
        raise OperationCleanupError(
            RuntimeError("Case body completed but cleanup did not"),
            failures,
        )
