# CAN多实例Case的软件流程回归。
# 职责：固定独立响应证明交错收发、Guard强断言和报告字段闭合。
# 边界：不操作硬件，不产生CAN HIL证据；不从TX请求生成RX数据。
# 依赖：真实Case、CAN公开Model、受限Mock及既有报告验证入口。

from dataclasses import replace
from unittest.mock import Mock

import pytest
from et_test_platform.drivers.can import (
    CanDriver,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanRxFifoStatus,
    CanRxFrame,
    CanTxStatus,
)
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import (
    assert_case_report,
    dependencies,
)
from et_test_platform.test_cases.can._support import loopback_ram
from et_test_platform.test_cases.can.test_can_p2 import (
    test_can_p2_004_instance_ram_isolation as run_case,
)


# 测试 Feature：全实例并存、错误Guard拒绝及PASS/FAIL报告闭合。
# 测试方法：三实例固定RX向量；分别破坏配置阶段Filter及最后实例尾Guard。
# 通过条件：所有RX就绪先于首次读取；坏Guard必须FAIL，每个实例均退出复位。
@pytest.mark.parametrize("fault", (None, "guard", "filter"))
def test_multi_instance_case_and_report(fault, tmp_path) -> None:

    support, resource, _, resets = dependencies()
    support.mapping.CAN_RAM_TEST_REGIONS = {f"can{i}": ((0, 16384),) for i in range(3)}
    support.mapping.CAN_CONCURRENT_RAM_REGIONS = {f"can{i}": (i * 4096, 4096) for i in range(3)}
    supports, timeline = [], []

    # 每个Fake只提供独立确定的响应；配置读回不读取Case发来的SET参数。
    for index in range(3):
        driver = Mock(spec=CanDriver)
        driver.instance_id = index
        current = replace(support, handle=f"can{index}", can=driver)
        layout = loopback_ram(current)
        driver.ram_layout_get.return_value = replace(
            layout,
            std_offset=index * 4096 + 8,
            ext_offset=index * 4096 + 12,
            tx_offset=index * 4096 + 12,
            event_offset=index * 4096 + 28,
            rx0_offset=index * 4096 + 28,
            rx1_offset=index * 4096 + 92,
            rx_buffer_offset=index * 4096 + 92,
        )
        first_filter = CanFilter(
            CanFilterType.DUAL, CanFilterAction.FIFO0, 0x100 + index, 0x100 + index
        )
        if fault == "filter" and index == 0:
            first_filter = replace(first_filter, id1=0x102, id2=0x102)
        last_filter = CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x500, 0x500)
        driver.filter_get.side_effect = [first_filter, last_filter if index == 2 else first_filter]
        driver.wait_tx_complete.return_value = CanTxStatus(0, 1, 0, 1, 0, 0, False)
        driver.wait_rx_available.side_effect = lambda *a, i=index, **kw: (
            timeline.append(("ready", i)) or CanRxFifoStatus(1, 0, 1, False, False)
        )
        vectors = [
            CanRxFrame(
                0x100 + index,
                CanFrameFlags(0),
                8,
                0,
                0,
                False,
                0,
                bytes((index, 0, 0, 0, 0x75, 0x86, 0x97, 0xA8)),
            )
        ]
        if index == 2:
            vectors.append(
                CanRxFrame(
                    0x500,
                    CanFrameFlags(0),
                    8,
                    0,
                    0,
                    False,
                    1,
                    bytes.fromhex("31 42 53 64 75 86 97 A8"),
                )
            )
        driver.rx_read.side_effect = lambda *a, i=index, values=vectors: (
            timeline.append(("read", i)) or values.pop(0)
        )
        driver.rx_fifo_status_get.return_value = CanRxFifoStatus(0, 1, 1, False, False)
        tail = 0 if fault == "guard" and index == 2 else 0xA5A50000 | index
        driver.ram_words_read.side_effect = [(0x5A5A0000 | index,), (tail,)]
        supports.append(current)

    properties = []

    # 保留真实Case的逐次Evidence，供同一报告模型检查，不补造字段。
    def record(key, value):
        properties.append((key, value))

    if fault:
        with pytest.raises(AssertionError):
            run_case(tuple(supports), resource, record)
    else:
        run_case(tuple(supports), resource, record)

    if fault == "filter":
        assert not timeline
    else:
        assert timeline[:3] == [("ready", 0), ("ready", 1), ("ready", 2)]
        assert timeline[3:6] == [("read", 2), ("read", 1), ("read", 0)]
    assert resets[-4:] == [("can", 0), ("can", 1), ("can", 2), ("resource",)]
    assert_case_report(properties, "CAN_P2_004", "FAIL" if fault else "PASS", tmp_path)
