# Framework Validation测试模块。
#
# 职责：验证FMAC DMA执行映射通过芯片Profile解析，且公共Case不保存芯片事实。
# 边界：不访问目标硬件，不执行DMA传输。
# 依赖：仅依赖pytest、FMAC Support和芯片Execution Mapping。

from __future__ import annotations

import pytest

from et_test_platform.core.errors import UnsupportedCapability
from et_test_platform.profiles.capabilities import load_packaged_chip_capabilities
from et_test_platform.test_cases.fmac._support import resolve_fmac_dma_route


def test_et6801_fmac_dma_route_matches_reviewed_execution_mapping() -> None:

    route = resolve_fmac_dma_route(
        load_packaged_chip_capabilities("et6801"),
        instance_id=0,
    )

    assert route.instance_id == 0
    assert route.controller == 0
    assert route.input_interface != route.output_interface
    assert route.input_request_id == 2
    assert route.output_request_id == 1
    assert route.fifo_address == 0x40204020
    assert route.transfer_width_bits == 16
    assert route.address_evidence
    assert route.request_evidence


def test_et6801_fmac_dma_route_rejects_unknown_instance() -> None:

    with pytest.raises(UnsupportedCapability, match="supports instance 0"):
        resolve_fmac_dma_route(
            load_packaged_chip_capabilities("et6801"),
            instance_id=1,
        )
