# Framework Validation测试模块。
#
# 职责：验证test_dma_extended_driver 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.drivers import crg as crg_module
from et_test_platform.drivers import dma as dma_module
from et_test_platform.drivers import sysctrl as sysctrl_module


class _Target:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int, bytes]] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        retry_safe: bool = False,
    ):
        del retry_safe
        self.calls.append((service_id, command_id, instance_id, body))
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=b"",
            ),
            object(),
        )


# Catch loss or overlap of the two compact handshake config bytes.
def test_dma_config_encodes_handshake_mode_and_polarity() -> None:
    assert hasattr(dma_module, "DmaHandshakeMode")
    assert hasattr(dma_module, "DmaHandshakePolarity")

    config = dma_module.DmaConfig(
        channel=3,
        source_address=0x20001000,
        destination_address=0x40002000,
        transfer_count=16,
        source_handshake_mode=dma_module.DmaHandshakeMode.SOFTWARE,
        destination_handshake_mode=dma_module.DmaHandshakeMode.HARDWARE,
        source_handshake_polarity=dma_module.DmaHandshakePolarity.ACTIVE_LOW,
        destination_handshake_polarity=(dma_module.DmaHandshakePolarity.ACTIVE_HIGH),
    )

    encoded = config.encode()
    assert len(encoded) == 64
    assert encoded[14:16] == b"\x03\x00"


# Catch silent reinterpretation of an unknown mode as a polarity bit.
def test_dma_config_rejects_unknown_handshake_enum_values() -> None:
    with pytest.raises(ValueError, match="handshake"):
        dma_module.DmaConfig(
            channel=0,
            source_address=0x20000000,
            destination_address=0x20000100,
            transfer_count=1,
            source_handshake_mode=2,  # type: ignore[arg-type]
        ).encode()


# Catch direction, request-kind, or active-state protocol drift.
def test_dma_driver_sends_typed_software_handshake_request() -> None:
    assert hasattr(dma_module.DmaCommand, "SOFTWARE_HANDSHAKE_REQUEST_SET")
    assert hasattr(dma_module, "DmaHandshakeTarget")
    assert hasattr(dma_module, "DmaSoftwareRequestKind")

    target = _Target()
    driver = dma_module.DmaDriver(target, instance_id=1)  # type: ignore[arg-type]
    driver.software_handshake_request_set(
        channel=5,
        target=dma_module.DmaHandshakeTarget.DESTINATION,
        request_kind=dma_module.DmaSoftwareRequestKind.SINGLE,
        active=True,
    )

    assert target.calls == [
        (
            dma_module.DMA_SERVICE_ID,
            int(dma_module.DmaCommand.SOFTWARE_HANDSHAKE_REQUEST_SET),
            1,
            b"\x05\x01\x01\x01",
        )
    ]


# Catch peripheral type, instance, or enable-state corruption.
def test_crg_driver_exposes_generic_clock_and_reset_commands() -> None:
    assert hasattr(crg_module.CrgCommand, "CLOCK_SET")
    assert hasattr(crg_module.CrgCommand, "RESET")

    target = _Target()
    driver = crg_module.CrgDriver(target)  # type: ignore[arg-type]
    driver.clock_set(crg_module.CrgPeripheral.DMA, instance=1, enabled=False)
    driver.reset(crg_module.CrgPeripheral.DMA, instance=1)

    assert target.calls == [
        (
            crg_module.CRG_SERVICE_ID,
            int(crg_module.CrgCommand.CLOCK_SET),
            0,
            b"\x01\x01\x00\x00",
        ),
        (
            crg_module.CRG_SERVICE_ID,
            int(crg_module.CrgCommand.RESET),
            0,
            b"\x01\x01\x00\x00",
        ),
    ]


# Catch DMAMUX route or release body corruption.
def test_sysctrl_driver_exposes_dma_request_routing_commands() -> None:

    target = _Target()
    driver = sysctrl_module.SysctrlDriver(target)  # type: ignore[arg-type]
    driver.configure_dma_request(
        controller=1,
        interface=2,
        endpoint=sysctrl_module.DmaEndpoint.UART_RX,
        instance=3,
        address=0x40502000,
    )
    driver.release_dma_request(controller=1, interface=2)

    assert target.calls == [
        (
            sysctrl_module.SYSCTRL_SERVICE_ID,
            int(sysctrl_module.SysctrlCommand.DMA_REQUEST_CONFIGURE),
            0,
            b"\x01\x02\x01\x03" + (0x40502000).to_bytes(8, "little"),
        ),
        (
            sysctrl_module.SYSCTRL_SERVICE_ID,
            int(sysctrl_module.SysctrlCommand.DMA_REQUEST_RELEASE),
            0,
            b"\x01\x02\x00\x00",
        ),
    ]
