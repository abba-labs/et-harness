# 暂缓Feature事实清单。
#
# 职责：记录当前证据链无法执行的Feature及明确原因。
# 边界：不伪造测试结果、不执行硬件命令，也不把缺失能力报告为PASS。
# 依赖：仅依赖pytest的显式Skip语义。

from __future__ import annotations


def _deferred_result(reason: str, *, handles_present: bool) -> dict[str, object]:
    return {
        "status": "DEFERRED",
        "reason": reason,
        "handles_present": handles_present,
    }


# 测试 Feature：
# UART RS485 普通、软件半双工和硬件半双工模式。
#
# 测试方法：
# 1. 待 bench 声明 RS485 收发器和方向控制后，按三种模式分别建立短帧。
# 2. 由 Peer 观察方向切换并校验 DUT 收发数据和总线冲突状态。
#
# 通过条件：
# 1. 每种已声明模式的短帧都完整收发，方向切换顺序正确。
# 2. 未声明收发器时不进入硬件结论，保留清晰的阻塞原因。
def _deferred_uart_p3_001_rs485_transfer_modes(
    uart_dut_handle=None,
    uart_peer_handle=None,
) -> dict[str, object]:
    return _deferred_result(
        "rs485_transceiver_and_direction_path_not_declared",
        handles_present=uart_dut_handle is not None and uart_peer_handle is not None,
    )


# 测试 Feature：
# UART RS485 DE/RE 极性和手动控制。
#
# 测试方法：
# 1. 待 bench 声明 DE/RE 数字观察端后，逐项配置高有效和低有效极性。
# 2. 由观察端记录实际电平，并在发送和接收边界确认方向许可。
#
# 通过条件：
# 1. 观察电平与配置极性一致，发送和接收不会同时错误驱动总线。
# 2. 缺少观察端时仅保留待执行定义，不伪造通过结果。
def _deferred_uart_p3_002_rs485_de_re_polarity(
    uart_dut_handle=None,
    uart_peer_handle=None,
) -> dict[str, object]:
    return _deferred_result(
        "rs485_de_re_observer_not_declared",
        handles_present=uart_dut_handle is not None and uart_peer_handle is not None,
    )


# 测试 Feature：
# UART RS485 发送到接收的 turnaround 时序。
#
# 测试方法：
# 1. 待独立数字观察器声明 tick 精度后，发送固定短帧并捕获方向边沿。
# 2. 计算 DE/RE 转换间隔，与配置值和观察器自申报容差比较。
#
# 通过条件：
# 1. 边沿顺序和转换间隔符合硬件设计契约。
# 2. 没有独立时序观察器时不将同源 Peer 对测当作绝对时序证据。
def _deferred_uart_p3_003_rs485_turnaround_timing(
    uart_dut_handle=None,
    uart_peer_handle=None,
) -> dict[str, object]:
    return _deferred_result(
        "independent_digital_timing_observer_not_declared",
        handles_present=uart_dut_handle is not None and uart_peer_handle is not None,
    )


# 测试 Feature：
# UART SIR 普通模式编码和解码。
#
# 测试方法：
# 1. 待 SIR 收发器或可信数字模型加入 bench 后，配置普通 SIR 并发送短 pattern。
# 2. 比较编码端和解码端数据，随后切回普通 UART 进行恢复验证。
#
# 通过条件：
# 1. SIR 数据完整一致且错误状态可清除。
# 2. 没有 SIR 数字路径时保持定义状态，不执行普通 UART 冒充测试。
def _deferred_uart_p3_004_sir_normal_mode(
    uart_dut_handle=None,
    uart_peer_handle=None,
) -> dict[str, object]:
    return _deferred_result(
        "sir_digital_path_not_declared",
        handles_present=uart_dut_handle is not None and uart_peer_handle is not None,
    )


# 测试 Feature：
# UART 低功耗 SIR 固定波特率路径。
#
# 测试方法：
# 1. 待低功耗 SIR 配测路径声明后，配置固定速率并执行最小双向帧。
# 2. 恢复普通 UART 并确认退出低功耗模式后收发正常。
#
# 通过条件：
# 1. 固定速率帧完整一致，非法速率被拒绝。
# 2. 缺少低功耗 SIR 路径时不输出硬件 PASS。
def _deferred_uart_p3_005_sir_low_power_mode(
    uart_dut_handle=None,
    uart_peer_handle=None,
) -> dict[str, object]:
    return _deferred_result(
        "low_power_sir_path_not_declared",
        handles_present=uart_dut_handle is not None and uart_peer_handle is not None,
    )


# 测试 Feature：
# UART 绝对波特率和位级时序精度。
#
# 测试方法：
# 1. 待独立时钟域观察器声明 tick/ppm 后，发送固定 0x55 交替 pattern。
# 2. 由观察器测量位宽和帧宽，并使用结果中的设备精度判断容差。
#
# 通过条件：
# 1. 测量波特率和位宽符合芯片规格。
# 2. 未接独立观察器时不使用同源对端推断绝对精度。
def _deferred_uart_p3_006_absolute_baudrate_and_bit_timing(
    uart_dut_handle=None,
    uart_peer_handle=None,
) -> dict[str, object]:
    return _deferred_result(
        "independent_baudrate_observer_not_declared",
        handles_present=uart_dut_handle is not None and uart_peer_handle is not None,
    )


# 测试 Feature：
# UART protection 访问和寄存器 timeout 恢复。
#
# 测试方法：
# 1. 待权限模型、fault 捕获和复位恢复流程声明后，分别验证允许与拒绝访问。
# 2. 在可恢复窗口内观察 timeout/fault，并用相同 handle 做最小恢复收发。
#
# 通过条件：
# 1. 允许、拒绝和 timeout 行为与设计契约一致，控制通道不被锁死。
# 2. 未声明权限和 fault 恢复路径时不执行危险访问。
def _deferred_uart_p3_008_protection_and_register_timeout(
    uart_dut_handle=None,
    uart_peer_handle=None,
) -> dict[str, object]:
    return _deferred_result(
        "protection_and_fault_recovery_contract_not_declared",
        handles_present=uart_dut_handle is not None,
    )
