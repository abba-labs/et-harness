# 暂缓Feature事实清单。
#
# 职责：记录当前证据链无法执行的Feature及明确原因。
# 边界：不伪造测试结果、不执行硬件命令，也不把缺失能力报告为PASS。
# 依赖：仅依赖pytest的显式Skip语义。

from __future__ import annotations


# Feature: Validate LLI fault reporting and post-fault recovery.
#
# Deferred: no approved invalid LLI address window is declared; keep this
# plan out of formal pytest collection until a safe window is documented.
def _deferred_dma_p2_003_lli_fault_and_recovery() -> None:
    pass


# Feature: Validate non-fatal DMA bus-error IRQ and recovery behavior.
#
# Deferred: no approved non-fatal DMA bus-fault address is declared; keep this
# plan out of formal pytest collection until a safe window is documented.
def _deferred_dma_p2_007_error_irq_and_recovery() -> None:
    pass


# Feature: Reserve handshake polarity coverage for a declared request source.
#
# Deferred: no controllable polarity source is declared in the board/profile;
# keep this plan out of formal pytest collection until one is available.
def _deferred_dma_p2_012_handshake_polarity() -> None:
    pass


# Feature: Validate core-context routing and safe TCM DMA access.
#
# Deferred: CORE1 and safe TCM windows are not declared; keep this plan out of
# formal pytest collection until those resource ranges are available.
def _deferred_dma_p2_014_core_context_and_tcm() -> None:
    pass


# p1_002 priority arbitration remains a requirement, not a formal hardware Case:
# completion order needs an independent observer; CHENREG polling is not accepted.
# p1_003 suspend/resume remains a requirement until an approved deterministic
# in-flight transfer window exists that can prove the suspend point safely.
# p3_001..p3_006 remain requirements until their semantic identity/snapshot
# evidence is independently approved; they must not appear as test_* + skip.
