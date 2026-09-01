# B&K Precision 9130B 状态寄存器控制与查询。
#
# 职责：映射 QUEStionable/OPERation 及各通道 ISUMmary 状态寄存器的原子读写命令。
# 边界：不轮询状态变化、不清理多个寄存器，也不把寄存器值解释为测试 PASS/FAIL。
# 依赖：仅依赖 ScpiSession 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import require_integer, require_register_value


# 提供 9130B 状态寄存器单命令控制；事件查询是否清零遵循仪器自身 SCPI 语义。
class Bk9130bStatusControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 复位仪器状态寄存器；只发送一次 STATus:PRESet。
    def preset(self) -> None:
        self._session.write("STATus:PRESet")

    # 查询 questionable 事件寄存器；读取后的清零行为由仪器按手册执行。
    def questionable_event_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:EVENt?"))

    # 查询 questionable 条件寄存器；查询过程不会修改使能配置。
    def questionable_condition_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:CONDition?"))

    # 设置 questionable 事件使能寄存器 0~255；只修改该寄存器。
    def questionable_enable_set(self, value: int) -> None:
        self._session.write(f"STATus:QUEStionable:ENABle {require_integer(value, 0, 255, 'value')}")

    # 查询 questionable 事件使能寄存器；查询过程不会修改寄存器。
    def questionable_enable_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:ENABle?"))

    # 查询 questionable 仪器事件汇总；只读取本次事件寄存器。
    def questionable_instrument_event_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:INSTrument:EVENt?"))

    # 设置 questionable 仪器使能寄存器；只修改该寄存器。
    def questionable_instrument_enable_set(self, value: int) -> None:
        normalized = require_register_value(value)
        self._session.write(f"STATus:QUEStionable:INSTrument:ENABle {normalized}")

    # 查询 questionable 仪器使能寄存器；查询过程不会修改寄存器。
    def questionable_instrument_enable_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:INSTrument:ENABle?"))

    # 查询 questionable 通道 1 事件汇总；读取后的事件清零行为由仪器固件决定。
    def questionable_summary1_event_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:INSTrument:ISUMmary1:EVENt?"))

    # 设置 questionable 通道 1 使能寄存器；只修改该通道状态寄存器。
    def questionable_summary1_enable_set(self, value: int) -> None:
        normalized = require_register_value(value)
        self._session.write(f"STATus:QUEStionable:INSTrument:ISUMmary1:ENABle {normalized}")

    # 查询 questionable 通道 1 使能寄存器；查询过程不会修改寄存器。
    def questionable_summary1_enable_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:INSTrument:ISUMmary1:ENABle?"))

    # 查询 questionable 通道 1 条件寄存器；查询过程不会修改使能配置。
    def questionable_summary1_condition_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:INSTrument:ISUMmary1:CONDition?"))

    # 查询 questionable 通道 2 事件汇总；读取后的事件清零行为由仪器固件决定。
    def questionable_summary2_event_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:INSTrument:ISUMmary2:EVENt?"))

    # 设置 questionable 通道 2 使能寄存器；只修改该通道状态寄存器。
    def questionable_summary2_enable_set(self, value: int) -> None:
        normalized = require_register_value(value)
        self._session.write(f"STATus:QUEStionable:INSTrument:ISUMmary2:ENABle {normalized}")

    # 查询 questionable 通道 2 使能寄存器；查询过程不会修改寄存器。
    def questionable_summary2_enable_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:INSTrument:ISUMmary2:ENABle?"))

    # 查询 questionable 通道 2 条件寄存器；查询过程不会修改使能配置。
    def questionable_summary2_condition_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:INSTrument:ISUMmary2:CONDition?"))

    # 查询 questionable 通道 3 事件汇总；读取后的事件清零行为由仪器固件决定。
    def questionable_summary3_event_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:INSTrument:ISUMmary3:EVENt?"))

    # 设置 questionable 通道 3 使能寄存器；只修改该通道状态寄存器。
    def questionable_summary3_enable_set(self, value: int) -> None:
        normalized = require_register_value(value)
        self._session.write(f"STATus:QUEStionable:INSTrument:ISUMmary3:ENABle {normalized}")

    # 查询 questionable 通道 3 使能寄存器；查询过程不会修改寄存器。
    def questionable_summary3_enable_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:INSTrument:ISUMmary3:ENABle?"))

    # 查询 questionable 通道 3 条件寄存器；查询过程不会修改使能配置。
    def questionable_summary3_condition_get(self) -> int:
        return int(self._session.query_text("STATus:QUEStionable:INSTrument:ISUMmary3:CONDition?"))

    # 查询 operation 事件寄存器；读取后的清零行为由仪器按手册执行。
    def operation_event_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:EVENt?"))

    # 查询 operation 条件寄存器；查询过程不会修改使能配置。
    def operation_condition_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:CONDition?"))

    # 设置 operation 事件使能寄存器 0~255；只修改该寄存器。
    def operation_enable_set(self, value: int) -> None:
        self._session.write(f"STATus:OPERation:ENABle {require_integer(value, 0, 255, 'value')}")

    # 查询 operation 事件使能寄存器；查询过程不会修改寄存器。
    def operation_enable_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:ENABle?"))

    # 查询 operation 仪器事件汇总；只读取本次事件寄存器。
    def operation_instrument_event_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:INSTrument:EVENt?"))

    # 设置 operation 仪器使能寄存器；只修改该寄存器。
    def operation_instrument_enable_set(self, value: int) -> None:
        self._session.write(f"STATus:OPERation:INSTrument:ENABle {require_register_value(value)}")

    # 查询 operation 仪器使能寄存器；查询过程不会修改寄存器。
    def operation_instrument_enable_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:INSTrument:ENABle?"))

    # 查询 operation 通道 1 事件汇总；读取后的事件清零行为由仪器固件决定。
    def operation_summary1_event_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:INSTrument:ISUMmary1:EVENt?"))

    # 设置 operation 通道 1 使能寄存器；只修改该通道状态寄存器。
    def operation_summary1_enable_set(self, value: int) -> None:
        normalized = require_register_value(value)
        self._session.write(f"STATus:OPERation:INSTrument:ISUMmary1:ENABle {normalized}")

    # 查询 operation 通道 1 使能寄存器；查询过程不会修改寄存器。
    def operation_summary1_enable_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:INSTrument:ISUMmary1:ENABle?"))

    # 查询 operation 通道 1 条件寄存器；查询过程不会修改使能配置。
    def operation_summary1_condition_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:INSTrument:ISUMmary1:CONDition?"))

    # 查询 operation 通道 2 事件汇总；读取后的事件清零行为由仪器固件决定。
    def operation_summary2_event_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:INSTrument:ISUMmary2:EVENt?"))

    # 设置 operation 通道 2 使能寄存器；只修改该通道状态寄存器。
    def operation_summary2_enable_set(self, value: int) -> None:
        normalized = require_register_value(value)
        self._session.write(f"STATus:OPERation:INSTrument:ISUMmary2:ENABle {normalized}")

    # 查询 operation 通道 2 使能寄存器；查询过程不会修改寄存器。
    def operation_summary2_enable_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:INSTrument:ISUMmary2:ENABle?"))

    # 查询 operation 通道 2 条件寄存器；查询过程不会修改使能配置。
    def operation_summary2_condition_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:INSTrument:ISUMmary2:CONDition?"))

    # 查询 operation 通道 3 事件汇总；读取后的事件清零行为由仪器固件决定。
    def operation_summary3_event_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:INSTrument:ISUMmary3:EVENt?"))

    # 设置 operation 通道 3 使能寄存器；只修改该通道状态寄存器。
    def operation_summary3_enable_set(self, value: int) -> None:
        normalized = require_register_value(value)
        self._session.write(f"STATus:OPERation:INSTrument:ISUMmary3:ENABle {normalized}")

    # 查询 operation 通道 3 使能寄存器；查询过程不会修改寄存器。
    def operation_summary3_enable_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:INSTrument:ISUMmary3:ENABle?"))

    # 查询 operation 通道 3 条件寄存器；查询过程不会修改使能配置。
    def operation_summary3_condition_get(self) -> int:
        return int(self._session.query_text("STATus:OPERation:INSTrument:ISUMmary3:CONDition?"))
