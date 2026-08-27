# Framework Validation测试模块。
#
# 职责：验证test_uart_driver 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import struct

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.uart import (
    BUSY_DETECT_RESULT,
    CAPABILITIES,
    CAPTURE_HEADER,
    FIFO_ACCESS_CONFIG,
    FIFO_RX_WRITE,
    FIFO_TX_VALUE,
    SHADOW_FIFO_CONFIG,
    TRANSFERRED,
    UART_SERVICE_ID,
    UartBusyDetectResult,
    UartCommand,
    UartDmaEndpoint,
    UartDmaMode,
    UartDriver,
    UartErrorFlag,
    UartFeature,
    UartIrqSource,
    UartIrqState,
    UartModemStatus,
    UartParity,
    UartShadowFifoState,
    UartSnapshot,
    UartStatus,
    UartStopBits,
)


class _Target:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int, bytes]] = []
        self.last_write = b""
        self.capture_starts = 0

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
    ):
        self.calls.append((service_id, command_id, instance_id, body))
        response = b""
        if command_id == UartCommand.CAPABILITIES_GET:
            response = CAPABILITIES.pack(
                int(UartFeature.RX_DMA | UartFeature.TX_DMA),
                1,
                12_000_000,
                65535,
                65535,
            )
        elif command_id == UartCommand.DMA_ENDPOINT_GET:
            response = (0x40501000 + body[0] * 4).to_bytes(8, "little")
        elif command_id == UartCommand.WRITE:
            self.last_write = body[4:]
            response = TRANSFERRED.pack(len(self.last_write))
        elif command_id == UartCommand.READ_EXACT:
            length = int.from_bytes(body[:4], "little")
            response = bytes(range(length))
        elif command_id == UartCommand.CAPTURE_START:
            self.capture_starts += 1
        elif command_id == UartCommand.CAPTURE_GET:
            data = self.last_write if self.capture_starts > 1 else b"captured"
            response = CAPTURE_HEADER.pack(0, len(data), len(data)) + data
        elif command_id == UartCommand.IRQ_STATE_GET:
            response = struct.pack("<6I", 0, 0, 0, 0, 0, 0)
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=response,
            ),
            object(),
        )


class _IrqSequenceTarget:
    def __init__(self) -> None:
        self.states = iter(
            (
                (1, 0, 0, 3, 0, 0),
                (1, int(UartIrqSource.CHARACTER_TIMEOUT), 0, 4, 0, 0),
            )
        )

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        timeout_s: float | None = None,
    ):
        del body, timeout_s
        assert command_id == UartCommand.IRQ_STATE_GET
        response = struct.pack("<6I", *next(self.states))
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=response,
            ),
            object(),
        )


# PC semantics must match the normalized UART Wrap error bit contract.
def test_uart_error_flags_are_stable_wrap_wire_bits() -> None:

    assert int(UartErrorFlag.OVERRUN) == 1 << 0
    assert int(UartErrorFlag.PARITY) == 1 << 1
    assert int(UartErrorFlag.FRAMING) == 1 << 2
    assert int(UartErrorFlag.BREAK) == 1 << 3
    assert int(UartErrorFlag.RX_FIFO) == 1 << 4


def test_uart_wait_irq_event_polls_until_source_and_counter_advance() -> None:
    now = 0.0

    def clock() -> float:
        return now

    def sleep(duration: float) -> None:
        nonlocal now
        now += duration

    uart = UartDriver(
        _IrqSequenceTarget(),  # type: ignore[arg-type]
        clock=clock,
        sleep=sleep,
    )

    state = uart.wait_irq_event(
        UartIrqSource.CHARACTER_TIMEOUT,
        3,
        timeout_s=0.1,
        poll_interval_s=0.01,
    )

    assert state.event_count == 4
    assert state.pending_mask == int(UartIrqSource.CHARACTER_TIMEOUT)


def test_uart_driver_uses_selected_instance_for_all_operations() -> None:
    target = _Target()
    uart = UartDriver(target, instance_id=5)  # type: ignore[arg-type]

    uart.initialize(baudrate=115200)
    caps = uart.capabilities_get()
    endpoint = uart.dma_endpoint_get(UartDmaEndpoint.RX)
    uart.dma_enable_set(True)
    assert uart.write(b"abc") == 3
    assert uart.read_exact(3) == b"\x00\x01\x02"
    uart.capture_start(8)
    capture = uart.capture_get()
    assert uart.exchange(b"xyz") == b"xyz"
    uart.capture_cancel()
    uart.deinitialize()

    assert all(call[0] == UART_SERVICE_ID for call in target.calls)
    assert all(call[2] == 5 for call in target.calls)
    assert caps.features == UartFeature.RX_DMA | UartFeature.TX_DMA
    assert endpoint == 0x40501004
    assert capture.complete
    assert capture.data == b"captured"


class _ExtendedTarget:
    def __init__(self, *, response_override: dict[int, bytes] | None = None):
        self.calls: list[tuple[int, int, int, bytes]] = []
        self.response_override = response_override or {}

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
    ):
        self.calls.append((service_id, command_id, instance_id, body))
        responses = {
            int(UartCommand.SNAPSHOT_GET): struct.pack(
                "<8I", 0xC800, 0x0102, 0x6801, 0xA5A5, 0x55, 0xAA, 3, 4
            ),
            int(UartCommand.STATUS_GET): struct.pack("<6I", 0x60, 0x03, 2, 1, 0, 0),
            int(UartCommand.IRQ_STATE_GET): struct.pack("<6I", 0x03, 0x01, 0x01, 7, 0, 0),
            int(UartCommand.WRITE_9BIT): struct.pack("<I", 2),
            int(UartCommand.READ_9BIT): struct.pack("<2H", 0x101, 0x055),
            int(UartCommand.MODEM_STATUS_GET): struct.pack("<4I", 0x03, 0x01, 0x02, 0x04),
        }
        response = self.response_override.get(int(command_id), responses.get(int(command_id), b""))
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=response,
            ),
            object(),
        )


def test_uart_extended_commands_and_wire_layout() -> None:
    target = _ExtendedTarget()
    uart = UartDriver(target, instance_id=7)  # type: ignore[arg-type]

    snapshot = uart.snapshot_get()
    uart.software_reset()
    uart.loopback_set(True)
    uart.fifo_config(
        enabled=True,
        tx_threshold=2,
        rx_threshold=4,
        dma_mode=UartDmaMode.MULTI,
    )
    status = uart.status_get()
    uart.irq_config(UartIrqSource.RX_READY | UartIrqSource.ERROR, True, 3)
    irq_state = uart.irq_state_get()
    uart.break_set(True)
    uart.halt_set(True)
    uart.dma_mode_set(UartDmaMode.SINGLE)
    uart.nine_bit_config(enabled=True, address_match=True, address=0x55)
    assert uart.write_9bit((0x1FF, 0x055), max_polls=10) == 2
    assert uart.read_9bit(2, max_polls=10) == (0x101, 0x055)
    uart.flow_control_set(enabled=True, rts_polarity=1, cts_polarity=0)
    uart.modem_control_set(rts=True, dtr=False)
    modem = uart.modem_status_get()

    assert snapshot == UartSnapshot(
        component_parameter=0xC800,
        component_version=0x0102,
        peripheral_id=0x6801,
        scratch=0xA5A5,
        uart_status=0x55,
        line_status=0xAA,
        tx_fifo_level=3,
        rx_fifo_level=4,
    )
    assert snapshot.component_parameter == 0xC800
    assert snapshot.component_version == 0x0102
    assert snapshot.peripheral_id == 0x6801
    assert snapshot.scratch == 0xA5A5
    assert snapshot.uart_status == 0x55
    assert snapshot.line_status == 0xAA
    assert status == UartStatus(0x60, 0x03, 2, 1, 0, 0)
    assert irq_state == UartIrqState(0x03, 0x01, 0x01, 7, 0, 0)
    assert modem == UartModemStatus(0x03, 0x01, 0x02, 0x04)
    assert modem.input_flags == 0x03
    assert modem.delta_flags == 0x01
    assert modem.output_flags == 0x02
    assert modem.raw_status == 0x04

    expected_ids = list(range(0x000C, 0x001C))
    assert [call[1] for call in target.calls] == expected_ids
    assert all(call[0] == UART_SERVICE_ID and call[2] == 7 for call in target.calls)
    assert target.calls[2][3] == b"\x01\x00\x00\x00"
    assert target.calls[3][3] == b"\x01\x02\x04\x02"
    assert target.calls[5][3] == struct.pack("<IBB2x", 0x05, 1, 3)
    assert target.calls[8][3] == b"\x01\x00\x00\x00"
    assert target.calls[9][3] == b"\x01\x00\x00\x00"
    assert target.calls[10][3] == struct.pack("<BBH", 1, 1, 0x55)
    assert target.calls[11][3] == struct.pack("<II2H", 2, 1, 0x1FF, 0x055)
    assert target.calls[12][3] == struct.pack("<II", 2, 1)
    assert target.calls[13][3] == b"\x01\x01\x00\x00"
    assert target.calls[14][3] == b"\x01\x00\x00\x00"


def test_uart_line_configuration_uses_canonical_wire_values() -> None:
    target = _ExtendedTarget()
    uart = UartDriver(target, instance_id=4)  # type: ignore[arg-type]

    # Legacy integer 2 means two stop bits to existing callers, but the
    # canonical wire value for two stop bits is 3.
    uart.initialize(baudrate=230400, data_bits=7, stop_bits=2, parity=2)
    uart.configure_extended(
        baudrate=230400,
        data_bits=5,
        stop_bits=UartStopBits.ONE_AND_HALF,
        parity=UartParity.STICK_ONE,
    )
    uart.configure_extended(
        baudrate=230400,
        data_bits=7,
        stop_bits=UartStopBits.TWO,
        parity=UartParity.NONE,
    )

    assert target.calls[0][1] == UartCommand.INITIALIZE
    assert target.calls[0][3] == struct.pack("<IBBBB", 230400, 7, 3, 2, 0)
    assert target.calls[1][3] == struct.pack("<IBBBB", 230400, 5, 2, 4, 0)
    assert target.calls[2][3] == struct.pack("<IBBBB", 230400, 7, 3, 0, 0)


def test_uart_line_configuration_rejects_invalid_semantics_locally() -> None:
    target = _ExtendedTarget()
    uart = UartDriver(target)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="5 and 8"):
        uart.initialize(baudrate=115200, data_bits=9)
    with pytest.raises(ValueError, match="1.5 stop bits"):
        uart.configure_extended(
            baudrate=115200,
            data_bits=7,
            stop_bits=UartStopBits.ONE_AND_HALF,
        )

    assert target.calls == []


@pytest.mark.parametrize(
    ("method", "args", "kwargs"),
    [
        ("dma_mode_set", (99,), {}),
        ("nine_bit_config", (), {"enabled": True, "address": 0x100}),
        ("write_9bit", ((0x200,),), {}),
        ("write_9bit", ((),), {}),
        ("write_9bit", (tuple(0 for _ in range(257)),), {}),
        ("read_9bit", (0,), {}),
        ("read_9bit", (257,), {}),
        ("flow_control_set", (), {"enabled": True, "rts_polarity": 2}),
        ("irq_config", (1 << 32, True, 0), {}),
    ],
)
def test_uart_extended_commands_reject_invalid_values(
    method: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> None:
    uart = UartDriver(_ExtendedTarget())  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        getattr(uart, method)(*args, **kwargs)


@pytest.mark.parametrize(
    ("method", "response_size"),
    [
        ("snapshot_get", 32),
        ("status_get", 24),
        ("irq_state_get", 20),
        ("modem_status_get", 16),
    ],
)
def test_uart_extended_results_reject_wrong_response_length(
    method: str, response_size: int
) -> None:
    target = _ExtendedTarget(response_override={int(getattr(UartCommand, method.upper())): b"bad"})
    uart = UartDriver(target)  # type: ignore[arg-type]
    with pytest.raises(ProtocolError):
        getattr(uart, method)()


def test_uart_void_extended_commands_reject_nonempty_response() -> None:
    target = _ExtendedTarget(response_override={int(UartCommand.SOFTWARE_RESET): b"unexpected"})
    uart = UartDriver(target)  # type: ignore[arg-type]
    with pytest.raises(ProtocolError):
        uart.software_reset()


class _AtomicTarget:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int, bytes]] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
    ):
        self.calls.append((service_id, command_id, instance_id, body))
        responses = {
            int(UartCommand.WRITE_PARTIAL): TRANSFERRED.pack(2),
            int(UartCommand.BUSY_DETECT_TRIGGER): BUSY_DETECT_RESULT.pack(
                0x01, 0x70, 0x01, 1, 1, 1, 1, 1
            ),
            int(UartCommand.SHADOW_FIFO_CONFIG): SHADOW_FIFO_CONFIG.pack(1, 8, 4, 0),
            int(UartCommand.FIFO_ACCESS_SET): FIFO_ACCESS_CONFIG.pack(1),
            int(UartCommand.FIFO_TX_READ): FIFO_TX_VALUE.pack(0xA5),
        }
        response = responses.get(int(command_id), b"")
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=response,
            ),
            object(),
        )


def test_uart_atomic_operations_use_stable_wire_layouts() -> None:
    target = _AtomicTarget()
    uart = UartDriver(target, instance_id=3)  # type: ignore[arg-type]

    assert uart.write_partial(b"abc") == 2
    busy = uart.busy_detect_trigger()
    shadow = uart.shadow_fifo_config(True, 8, 4)
    assert uart.test_fifo_access_set(True)
    assert uart.test_fifo_tx_read() == 0xA5
    uart.test_fifo_rx_write(0x5A, parity_error=True, framing_error=False)

    assert busy == UartBusyDetectResult(
        pre_trigger_usr=0x01,
        observed_iir=0x70,
        observed_usr=0x01,
        trigger_count=1,
        cleared=True,
        recovered=True,
        busy_observed=True,
        interrupt_observed=True,
    )
    assert shadow == UartShadowFifoState(True, 8, 4)
    assert [call[1] for call in target.calls] == [
        UartCommand.WRITE_PARTIAL,
        UartCommand.BUSY_DETECT_TRIGGER,
        UartCommand.SHADOW_FIFO_CONFIG,
        UartCommand.FIFO_ACCESS_SET,
        UartCommand.FIFO_TX_READ,
        UartCommand.FIFO_RX_WRITE,
    ]
    assert target.calls[0][3] == b"abc"
    assert target.calls[2][3] == SHADOW_FIFO_CONFIG.pack(1, 8, 4, 0)
    assert target.calls[3][3] == FIFO_ACCESS_CONFIG.pack(1)
    assert target.calls[5][3] == FIFO_RX_WRITE.pack(0x5A, 1, 0, 0)


def test_uart_driver_modes_own_single_ip_cleanup_in_stable_order() -> None:
    target = _AtomicTarget()
    uart = UartDriver(target, instance_id=2)  # type: ignore[arg-type]

    with (
        uart.initialized_mode(baudrate=115200),
        uart.loopback_mode(),
        uart.irq_mode(UartIrqSource.RX_READY, priority=3),
        uart.capture_mode(),
    ):
        uart.capture_start(4)

    assert [call[1] for call in target.calls] == [
        UartCommand.INITIALIZE,
        UartCommand.LOOPBACK_SET,
        UartCommand.IRQ_CONFIG,
        UartCommand.CAPTURE_START,
        UartCommand.CAPTURE_CANCEL,
        UartCommand.IRQ_CONFIG,
        UartCommand.LOOPBACK_SET,
        UartCommand.DEINITIALIZE,
    ]
    assert target.calls[1][3] == b"\x01\x00\x00\x00"
    assert target.calls[4][3] == b""
    assert target.calls[5][3][4] == 0
    assert target.calls[6][3] == b"\x00\x00\x00\x00"


def test_uart_driver_modes_cleanup_after_case_failure() -> None:
    target = _AtomicTarget()
    uart = UartDriver(target)  # type: ignore[arg-type]

    with (
        pytest.raises(RuntimeError, match="case failure"),
        uart.loopback_mode(),
        uart.capture_mode(),
    ):
        raise RuntimeError("case failure")

    assert [call[1] for call in target.calls] == [
        UartCommand.LOOPBACK_SET,
        UartCommand.CAPTURE_CANCEL,
        UartCommand.LOOPBACK_SET,
    ]


def test_uart_extended_modes_restore_each_owned_state() -> None:
    target = _AtomicTarget()
    uart = UartDriver(target)  # type: ignore[arg-type]

    with (
        uart.deinitialize_on_exit(),
        uart.flow_control_disable_on_exit(),
        uart.modem_outputs_release_on_exit(),
        uart.break_release_on_exit(),
        uart.halt_mode(),
        uart.fifo_access_mode() as fifo_access_enabled,
    ):
        uart.flow_control_set(True)
        uart.modem_control_set(True, True)
        uart.break_set(True)
        assert fifo_access_enabled

    assert [call[1] for call in target.calls] == [
        UartCommand.HALT_SET,
        UartCommand.FIFO_ACCESS_SET,
        UartCommand.FLOW_CONTROL_SET,
        UartCommand.MODEM_CONTROL_SET,
        UartCommand.BREAK_SET,
        UartCommand.FIFO_ACCESS_SET,
        UartCommand.HALT_SET,
        UartCommand.BREAK_SET,
        UartCommand.MODEM_CONTROL_SET,
        UartCommand.FLOW_CONTROL_SET,
        UartCommand.DEINITIALIZE,
    ]


def test_uart_loopback_disable_on_exit_preserves_direct_setup_timing() -> None:
    target = _AtomicTarget()
    uart = UartDriver(target)  # type: ignore[arg-type]

    with uart.loopback_disable_on_exit():
        uart.loopback_set(True)

    assert [call[1] for call in target.calls] == [
        UartCommand.LOOPBACK_SET,
        UartCommand.LOOPBACK_SET,
    ]
