# Framework Validation测试模块。
#
# 职责：验证test_public_api_and_wire_baseline 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from et_test_platform.clients import TargetClient
from et_test_platform.drivers.crc import CRC_SERVICE_ID
from et_test_platform.drivers.crg import CRG_CONTROL, CRG_SERVICE_ID, CrgCommand, CrgDriver
from et_test_platform.drivers.dma import (
    CAPABILITIES,
    CHANNEL,
    DMA_CONFIG,
    DMA_SERVICE_ID,
    DmaAddressMode,
    DmaBurst,
    DmaCommand,
    DmaConfig,
    DmaConfigFlag,
    DmaDriver,
    DmaFifoMode,
    DmaHandshakeMode,
    DmaHandshakePolarity,
    DmaTransferType,
    DmaUpdateMode,
    DmaWidth,
)
from et_test_platform.drivers.framework import (
    FRAMEWORK_SERVICE_ID,
    FrameworkCommand,
    FrameworkDriver,
)
from et_test_platform.drivers.resource import (
    CREATE_REQUEST,
    RESOURCE_REF,
    RESOURCE_SERVICE_ID,
    ResourceCommand,
    ResourceDriver,
)
from et_test_platform.drivers.sysctrl import (
    DMA_ROUTE,
    DMA_ROUTE_RELEASE,
    SYSCTRL_SERVICE_ID,
    SysctrlCommand,
    SysctrlDriver,
)
from et_test_platform.drivers.uart import (
    UART_CONFIG,
    UART_SERVICE_ID,
    UartCommand,
    UartDriver,
)


# Directory refactors must preserve the established public import surface.
def test_public_driver_imports_remain_available() -> None:

    assert TargetClient.__name__ == "TargetClient"
    assert FrameworkDriver.__name__ == "FrameworkDriver"
    assert ResourceDriver.__name__ == "ResourceDriver"
    assert CrgDriver.__name__ == "CrgDriver"
    assert DmaDriver.__name__ == "DmaDriver"
    assert SysctrlDriver.__name__ == "SysctrlDriver"
    assert UartDriver.__name__ == "UartDriver"


# Published IDs cannot be silently reused while later phases migrate Wire V2.
def test_service_and_command_ids_are_stable() -> None:

    assert FRAMEWORK_SERVICE_ID == 0x0000
    assert RESOURCE_SERVICE_ID == 0x0010
    assert SYSCTRL_SERVICE_ID == 0x0011
    assert CRG_SERVICE_ID == 0x0012
    assert DMA_SERVICE_ID == 0x0100
    assert UART_SERVICE_ID == 0x0101
    assert CRC_SERVICE_ID == 0x0102

    assert int(FrameworkCommand.HELLO) == 0x0001
    assert int(ResourceCommand.CREATE) == 0x0002
    assert int(SysctrlCommand.DMA_REQUEST_CONFIGURE) == 0x0001
    assert int(CrgCommand.CLOCK_SET) == 0x0001
    assert int(DmaCommand.CHANNEL_CONFIGURE) == 0x0004
    assert int(DmaCommand.LLI_DESCRIPTOR_INIT) == 0x0014
    assert int(DmaCommand.CHANNEL_START_WAIT) == 0x0018
    assert int(DmaCommand.CHANNELS_START_WAIT_ORDER) == 0x001B
    assert int(UartCommand.INITIALIZE) == 0x0004
    assert int(UartCommand.EXCHANGE) == 0x000B
    assert int(UartCommand.WRITE_9BIT) == 0x0017


# Structural refactors must not alter the legal legacy Wire layout.
def test_published_body_sizes_are_stable() -> None:

    assert CREATE_REQUEST.size == 8
    assert RESOURCE_REF.size == 16
    assert DMA_ROUTE.size == 12
    assert DMA_ROUTE_RELEASE.size == 4
    assert CRG_CONTROL.size == 4
    assert DMA_CONFIG.size == 64
    assert CHANNEL.size == 4
    assert CAPABILITIES.size == 20
    assert UART_CONFIG.size == 8


# Lock one legal full 64-byte DMA body independently of later package splitting.
def test_dma_config_representative_golden_vector_is_stable() -> None:

    config = DmaConfig(
        channel=0,
        transfer_type=DmaTransferType.PERIPHERAL_TO_PERIPHERAL,
        priority=2,
        source_width=DmaWidth.BITS_32,
        destination_width=DmaWidth.BITS_16,
        source_address_mode=DmaAddressMode.FIXED,
        destination_address_mode=DmaAddressMode.DECREMENT,
        source_burst=DmaBurst.ITEMS_256,
        destination_burst=DmaBurst.ITEMS_128,
        fifo_mode=DmaFifoMode.HALF_DEPTH,
        source_interface=10,
        destination_interface=11,
        source_update_mode=DmaUpdateMode.LINKED_LIST,
        destination_update_mode=DmaUpdateMode.RELOAD,
        source_handshake_mode=DmaHandshakeMode.SOFTWARE,
        destination_handshake_mode=DmaHandshakeMode.HARDWARE,
        source_handshake_polarity=DmaHandshakePolarity.ACTIVE_LOW,
        destination_handshake_polarity=DmaHandshakePolarity.ACTIVE_LOW,
        source_address=0x1122334455667788,
        destination_address=0x8877665544332211,
        transfer_count=0xAABBCCDD,
        flags=(
            DmaConfigFlag.SOURCE_GATHER
            | DmaConfigFlag.DESTINATION_SCATTER
            | DmaConfigFlag.INITIAL_DONE
        ),
        linked_list_address=0x0123456789ABCDEF,
        source_gather_interval=0x11121314,
        source_gather_count=0x21222324,
        destination_scatter_interval=0x31323334,
        destination_scatter_count=0x41424344,
    )

    assert config.encode().hex() == (
        "000302020102010706010a0b02010302"
        "88776655443322111122334455667788"
        "ddccbbaa07000000efcdab8967452301"
        "14131211242322213433323144434241"
    )
