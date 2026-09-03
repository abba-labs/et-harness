# Framework Validation测试模块。
#
# 职责：验证test_firmware_config_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from et_test_platform.communication.protocols.et_message import HEADER, Status
from et_test_platform.drivers.crc import CRC_SERVICE_ID, CrcCommand
from et_test_platform.drivers.crg import CRG_SERVICE_ID, CrgCommand
from et_test_platform.drivers.dma import DMA_SERVICE_ID, DmaCommand
from et_test_platform.drivers.framework import (
    FRAMEWORK_INSTANCE_ID,
    FRAMEWORK_SERVICE_ID,
    FrameworkCommand,
)
from et_test_platform.drivers.sysctrl import (
    SYSCTRL_SERVICE_ID,
    SysctrlCommand,
)

PROJECT_ROOT = Path(__file__).parents[5]
GENERATED_FIRMWARE_PROJECT = (
    PROJECT_ROOT / "firmware" / "build" / "et6801" / "ET6801_Automated_Test.uvprojx"
)
BOARD_CONFIGS = (
    PROJECT_ROOT / "firmware" / "boards" / "et6801_fpga" / "et_board_config.h",
    PROJECT_ROOT / "firmware" / "boards" / "et6801_silicon" / "et_board_config.h",
)


def _keil_file_is_in_build(file: ET.Element) -> bool:
    return file.findtext("FileOption/CommonProperty/IncludeInBuild", "1") != "0"


def _c_integer(source: str, name: str) -> int:
    match = re.search(
        rf"\b{name}\s*(?:=|\s)\s*(0x[0-9a-fA-F]+|\d+)u?\b",
        source,
    )
    assert match is not None, name
    return int(match.group(1), 0)


def test_c_and_python_public_protocol_constants_match() -> None:
    message_header = (
        PROJECT_ROOT / "firmware" / "framework" / "include" / "et_message.h"
    ).read_text(encoding="utf-8")
    framework_header = (
        PROJECT_ROOT / "firmware" / "services" / "include" / "et_framework_service.h"
    ).read_text(encoding="utf-8")
    dma_header = (
        PROJECT_ROOT / "firmware" / "services" / "include" / "et_dma_service.h"
    ).read_text(encoding="utf-8")
    crc_header = (
        PROJECT_ROOT / "firmware" / "services" / "include" / "et_crc_service.h"
    ).read_text(encoding="utf-8")
    crg_header = (
        PROJECT_ROOT / "firmware" / "services" / "include" / "et_crg_service.h"
    ).read_text(encoding="utf-8")
    sysctrl_header = (
        PROJECT_ROOT / "firmware" / "services" / "include" / "et_sysctrl_service.h"
    ).read_text(encoding="utf-8")

    assert _c_integer(message_header, "ET_MESSAGE_HEADER_SIZE") == HEADER.size
    for status in Status:
        assert _c_integer(
            message_header,
            f"ET_STATUS_{status.name}",
        ) == int(status)
    assert (
        _c_integer(
            framework_header,
            "ET_FRAMEWORK_SERVICE_ID",
        )
        == FRAMEWORK_SERVICE_ID
    )
    assert (
        _c_integer(
            framework_header,
            "ET_FRAMEWORK_INSTANCE_ID",
        )
        == FRAMEWORK_INSTANCE_ID
    )
    for command in FrameworkCommand:
        assert _c_integer(
            framework_header,
            f"ET_FRAMEWORK_COMMAND_{command.name}",
        ) == int(command)
    assert _c_integer(dma_header, "ET_DMA_SERVICE_ID") == DMA_SERVICE_ID
    for command in DmaCommand:
        assert _c_integer(
            dma_header,
            f"ET_DMA_COMMAND_{command.name}",
        ) == int(command)
    assert _c_integer(crc_header, "ET_CRC_SERVICE_ID") == CRC_SERVICE_ID
    for command in CrcCommand:
        assert _c_integer(
            crc_header,
            f"ET_CRC_COMMAND_{command.name}",
        ) == int(command)
    assert _c_integer(crg_header, "ET_CRG_SERVICE_ID") == CRG_SERVICE_ID
    for command in CrgCommand:
        assert _c_integer(
            crg_header,
            f"ET_CRG_COMMAND_{command.name}",
        ) == int(command)
    assert _c_integer(sysctrl_header, "ET_SYSCTRL_SERVICE_ID") == SYSCTRL_SERVICE_ID
    for command in SysctrlCommand:
        assert _c_integer(
            sysctrl_header,
            f"ET_SYSCTRL_COMMAND_{command.name}",
        ) == int(command)


def test_protocol_and_target_client_do_not_bypass_service_layers() -> None:
    firmware_protocol = (
        PROJECT_ROOT / "firmware" / "framework" / "src" / "et_protocol.c"
    ).read_text(encoding="utf-8")
    firmware_runtime = (
        PROJECT_ROOT / "firmware" / "framework" / "include" / "et_runtime.h"
    ).read_text(encoding="utf-8")
    pc_target = (PROJECT_ROOT / "pc" / "et_test_platform" / "clients" / "target.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "ET_FRAMEWORK_COMMAND_",
        "ET_FRAMEWORK_SERVICE_ID",
        "ECHO",
        "VERSION_GET",
    ):
        assert forbidden not in firmware_protocol
    assert "et_control_uart.h" not in firmware_runtime
    assert "et_dma_manager.h" not in firmware_runtime
    assert "et_dma_manager_t" not in firmware_runtime
    assert "FrameworkCommand" not in pc_target
    assert "drivers.framework" not in pc_target


def test_every_control_uart_setting_lives_in_each_board_config() -> None:
    required = (
        "ET_SYSTEM_UPDATE_CORE_CLOCK",
        "ET_CORTEX_ENABLE_ICACHE",
        "ET_CONTROL_UART_ID",
        "ET_CONTROL_UART_BAUDRATE",
        "ET_CONTROL_UART_DATA_BITS",
        "ET_CONTROL_UART_PARITY",
        "ET_CONTROL_UART_STOP_BITS",
        "ET_CONTROL_UART_TX_GPIO_ID",
        "ET_CONTROL_UART_TX_FUNCTION_ID",
        "ET_CONTROL_UART_RX_GPIO_ID",
        "ET_CONTROL_UART_RX_FUNCTION_ID",
        "ET_CONTROL_UART_RX_MODE",
        "ET_CONTROL_UART_TX_MODE",
        "ET_CONTROL_UART_IRQ_PRIORITY",
        "ET_CONTROL_UART_RX_BUFFER_SIZE",
        "ET_CONTROL_UART_TX_BUFFER_SIZE",
    )

    for config in BOARD_CONFIGS:
        source = config.read_text(encoding="utf-8")
        for macro in required:
            assert f"#define {macro} " in source
        for forbidden in (
            " UART0",
            " GPIO12",
            " GPIO13",
            " UART0_IRQn",
            "GPIO12_MODE_",
            "GPIO13_MODE_",
        ):
            assert forbidden not in source


def test_board_layer_is_macro_only_and_selected_by_the_build() -> None:
    boards_root = PROJECT_ROOT / "firmware" / "boards"
    contract = (boards_root / "include" / "et_board_config_contract.h").read_text(encoding="utf-8")

    assert not list(boards_root.rglob("*.c"))
    assert '#include "et_board_config.h"' in contract
    assert "ET_TARGET_FPGA" not in contract
    assert "ET_TARGET_SILICON" not in contract
    assert "et6801_fpga" not in contract
    assert "et6801_silicon" not in contract


def test_physical_uart_route_is_private_to_chip_wrap_config() -> None:
    source = (
        PROJECT_ROOT / "firmware" / "chips" / "et6801" / "config" / "et_chip_wrap_config.h"
    ).read_text(encoding="utf-8")

    for required in (
        "ET_CHIP_UART_MAP_TABLE",
        "{ET6801_UART_LOGICAL_0, UART0, UART0_IRQn",
        "ET_CHIP_GPIO_MAP_TABLE",
        "{GPIO12, GPIO12, GPIO12_MODE_GPIO12",
        "ET_GPIO_FUNCTION_UART_TX, GPIO12_MODE_UART0_TX",
        "{GPIO13, GPIO13, GPIO13_MODE_GPIO13",
        "ET_GPIO_FUNCTION_UART_RX, GPIO13_MODE_UART0_RX",
    ):
        assert required in source

    # One-off aliases make the chip fact file harder to review; facts belong
    # directly in one table entry per logical instance.
    for forbidden in (
        "ET_CHIP_UART0_INSTANCE",
        "ET_CHIP_UART0_PHYSICAL_IRQn",
        "ET_CHIP_GPIO12_PHYSICAL_PIN",
        "ET_CHIP_GPIO13_PHYSICAL_PIN",
    ):
        assert forbidden not in source


def test_public_sources_do_not_select_a_chip_uart_or_pc_port() -> None:
    public_source = "\n".join(
        path.read_text(encoding="utf-8")
        for root in (
            PROJECT_ROOT / "firmware" / "application" / "src",
            PROJECT_ROOT / "firmware" / "framework" / "src",
        )
        for path in root.glob("*.c")
    )
    pc_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "pc" / "et_test_platform").rglob("*.py")
        if "framework_validation" not in path.parts
    )
    assert pc_source

    for forbidden in ("UART0", "UART1", "UART2", "UART3", "COM1", "COM2"):
        assert forbidden not in public_source
        assert forbidden not in pc_source

    for forbidden in ("et6x_", "et6801.h", "GPIO12", "GPIO13"):
        assert forbidden not in public_source


def test_control_uart_application_owns_init_order_and_isr() -> None:
    control_transport = (
        PROJECT_ROOT / "firmware" / "application" / "src" / "et_control_uart.c"
    ).read_text(encoding="utf-8")
    uart_wrap = (PROJECT_ROOT / "firmware" / "wrap" / "src" / "et_uart_wrap.c").read_text(
        encoding="utf-8"
    )

    assert "control_uart_irq_handler" in control_transport
    assert "et_gpio_wrap_configure(" in control_transport
    assert "et_uart_wrap_init(" in control_transport
    assert "et_uart_wrap_get_irq_route(" in control_transport
    assert "et_irq_manager_bind(" in control_transport
    assert "et_irq_wrap_register(" not in control_transport
    assert "et_uart_wrap_get_interrupt_status(" in control_transport
    assert "control_uart_irq_handler" not in uart_wrap
    assert "callback" not in uart_wrap
    assert "Interrupt_" not in uart_wrap
    assert "NVIC_" not in uart_wrap
    assert "GPIO_" not in uart_wrap
    assert "SystemCoreClock" not in uart_wrap
    assert "SCB_" not in uart_wrap


def test_unimplemented_control_uart_dma_is_fail_closed() -> None:
    control_transport = (
        PROJECT_ROOT / "firmware" / "application" / "src" / "et_control_uart.c"
    ).read_text(encoding="utf-8")

    assert "(config->rx_mode == ET_CONTROL_UART_MODE_DMA)" in control_transport
    assert "(config->tx_mode == ET_CONTROL_UART_MODE_DMA)" in control_transport


def test_uart_wrap_public_contract_is_chip_neutral_and_extensible() -> None:
    header = (PROJECT_ROOT / "firmware" / "wrap" / "include" / "et_uart_wrap.h").read_text(
        encoding="utf-8"
    )

    for required in (
        "ET_UART_WRAP_API_VERSION",
        "struct_size",
        "api_version",
        "et_uart_wrap_get_capabilities",
        "reserved[ET_UART_WRAP_CONFIG_RESERVED_WORDS]",
        "reserved[ET_UART_WRAP_CAP_RESERVED_WORDS]",
        "et_uart_wrap_get_interrupt_status",
        "et_uart_wrap_enable_interrupts",
    ):
        assert required in header

    for forbidden in (
        "UART_Type",
        "IRQn_Type",
        "UART_ConfigParams",
        "GPIO12",
        "UART0_IRQn",
        "DRV_Status",
        "et6x_",
    ):
        assert forbidden not in header


def test_main_is_public_application_and_initializes_chip_primitives_before_runtime() -> None:
    main_path = PROJECT_ROOT / "firmware" / "application" / "src" / "main.c"
    source = main_path.read_text(encoding="utf-8")

    assert main_path.is_file()
    assert "et_system_wrap_update_core_clock(" in source
    assert "et_cortex_wrap_enable_instruction_cache(" in source
    assert "et_irq_wrap_init()" in source
    assert source.index("et_system_wrap_update_core_clock(") < source.index("et_runtime_init(")
    assert source.index("et_cortex_wrap_enable_instruction_cache(") < source.index(
        "et_runtime_init("
    )
    assert source.index("et_irq_wrap_init()") < source.index("et_runtime_init(")
    assert "et6801" not in source.lower()
    assert "et6x_" not in source
    assert not (PROJECT_ROOT / "firmware" / "chips" / "et6801" / "app" / "main.c").exists()


def test_application_manifest_prepares_board_test_uart_instances_before_runtime() -> None:
    main_source = (PROJECT_ROOT / "firmware" / "application" / "src" / "main.c").read_text(
        encoding="utf-8"
    )
    manifest_source = (
        PROJECT_ROOT / "firmware" / "application" / "src" / "et_service_manifest.c"
    ).read_text(encoding="utf-8")
    board_contract = (
        PROJECT_ROOT / "firmware" / "boards" / "include" / "et_board_config_contract.h"
    ).read_text(encoding="utf-8")

    assert "ET_TEST_UART_INSTANCE_IDS" in board_contract
    assert "ET_TEST_DMA_INSTANCE_IDS" in board_contract
    assert "et_crg_wrap_set_clock(" in manifest_source
    assert "et_crg_wrap_reset(" in manifest_source
    assert "et_service_manifest_prepare()" in main_source
    assert main_source.index("et_service_manifest_prepare()") < main_source.index(
        "et_runtime_init("
    )

    for board_name in ("et6801_fpga", "et6801_silicon"):
        board_source = (
            PROJECT_ROOT / "firmware" / "boards" / board_name / "et_board_config.h"
        ).read_text(encoding="utf-8")
        assert "ET_TEST_UART_INSTANCE_IDS" in board_source
        assert "ET_TEST_DMA_INSTANCE_IDS" in board_source


def test_service_registration_uses_declarative_groups_and_fails_closed() -> None:
    service_source = (PROJECT_ROOT / "firmware" / "services" / "src" / "et_services.c").read_text(
        encoding="utf-8"
    )
    service_header = (
        PROJECT_ROOT / "firmware" / "services" / "include" / "et_services.h"
    ).read_text(encoding="utf-8")
    main_source = (PROJECT_ROOT / "firmware" / "application" / "src" / "main.c").read_text(
        encoding="utf-8"
    )
    manifest_source = (
        PROJECT_ROOT / "firmware" / "application" / "src" / "et_service_manifest.c"
    ).read_text(encoding="utf-8")

    factory_header = (
        PROJECT_ROOT / "firmware" / "services" / "include" / "et_service_factory.h"
    ).read_text(encoding="utf-8")

    assert "et_service_factory_fn" in factory_header
    assert "et_service_group_t" in factory_header
    assert "const et_service_group_t *groups" in service_header
    assert "size_t group_count" in service_header
    assert (
        "services_config.groups = et_service_manifest_get(&services_config.group_count)"
        in main_source
    )
    assert "test_service_groups" not in main_source
    assert "test_uart_instances" not in main_source

    registered_ips = (
        "uart",
        "dma",
        "crc",
        "aes",
        "fmac",
        "cordic",
        "cpu",
        "stimer",
        "wdg",
        "spinlock",
        "ipcm",
        "syscnt",
    )

    for ip in registered_ips:
        assert f"test_{ip}_instances" in manifest_source
        assert f"test_{ip}_services" in manifest_source
        assert f"et_{ip}_service_create" in manifest_source

    # One match is the macro definition; every registered IP contributes one group.
    assert manifest_source.count("ET_SERVICE_GROUP(") == len(registered_ips) + 1
    assert "register_service_group(" in service_source
    assert "config->groups[group_index]" in service_source
    assert service_source.count("for (") == 2
    assert "uart_instance_ids" not in service_header
    assert "dma_instance_ids" not in service_header
    assert "crc_instance_ids" not in service_header
    assert "aes_instance_ids" not in service_header
    assert "cordic_instance_ids" not in service_header
    assert "et_uart_service_init(" not in service_source
    assert "et_dma_service_init(" not in service_source
    assert "et_crc_service_init(" not in service_source
    assert "et_aes_service_init(" not in service_source
    assert "et_cordic_service_init(" not in service_source
    assert "continue;" not in service_source


def test_generated_keil_project_has_all_target_specific_builds() -> None:
    project = GENERATED_FIRMWARE_PROJECT
    root = ET.parse(project).getroot()
    targets = {target.findtext("TargetName"): target for target in root.findall("Targets/Target")}

    assert set(targets) == {
        "ET6801_FPGA_ITCM",
        "ET6801_SILICON_FLASH",
        "ET6801_FPGA_MANUAL_FLASH",
        "ET6801_FPGA_CORE1_SMOKE_ITCM",
        "ET6801_SILICON_CORE1_LAUNCHER_FLASH",
    }
    assert "ET_TARGET_FPGA" in targets["ET6801_FPGA_ITCM"].findtext(
        "TargetOption/TargetArmAds/Cads/VariousControls/Define", ""
    )
    assert "ET_TARGET_SILICON" in targets["ET6801_SILICON_FLASH"].findtext(
        "TargetOption/TargetArmAds/Cads/VariousControls/Define", ""
    )
    manual_defines = targets["ET6801_FPGA_MANUAL_FLASH"].findtext(
        "TargetOption/TargetArmAds/Cads/VariousControls/Define", ""
    )
    assert "ET_TARGET_FPGA" in manual_defines
    assert "ET_MANUAL_TEST_ENABLE" in manual_defines
    flash_common = targets["ET6801_SILICON_FLASH"].find("TargetOption/TargetCommonOption")
    assert flash_common is not None
    assert flash_common.findtext("Device") == "ET6801"
    flash_driver = flash_common.findtext("FlashDriverDll", "")
    assert "ET6801.FLM" in flash_driver
    assert "-FS08000000" in flash_driver
    assert "-FL080000" in flash_driver

    common_groups = {
        "Application",
        "Board",
        "Framework",
        "Manual_Diagnostics",
        "Services",
        "Wrap",
        "Chip_Startup",
        "Chip_System",
        "Chip_Drivers",
    }
    for target in targets.values():
        groups = {group.findtext("GroupName") for group in target.findall("Groups/Group")}
        assert groups == common_groups
        assert "SDK_Startup" not in groups
        assert "SDK_System" not in groups
        assert "SDK_Drivers" not in groups

        group_files = {
            group.findtext("GroupName"): [
                file.findtext("FilePath") for file in group.findall("Files/File")
            ]
            for group in target.findall("Groups/Group")
        }
        assert len(group_files["Wrap"]) == len(set(group_files["Wrap"]))
        assert len(group_files["Wrap"]) == 19
        assert len(group_files["Services"]) == 17
        # SYSCNT使用现有Cortex SDK，不能遗漏新Service/Wrap或另造SDK转接文件。
        assert any(path and path.endswith("et_syscnt_wrap.c") for path in group_files["Wrap"])
        assert any(
            path and path.endswith("et_syscnt_service.c") for path in group_files["Services"]
        )
        assert any(path and path.endswith("et6x_cortex.c") for path in group_files["Chip_Drivers"])
        # 新增IPCM必须同时纳入本IP Driver、Wrap及Service，不能只增加文件计数。
        assert any(path and path.endswith("et_ipcm_wrap.c") for path in group_files["Wrap"])
        assert any(path and path.endswith("et_ipcm_service.c") for path in group_files["Services"])
        assert any(path and path.endswith("et6x_ipcm.c") for path in group_files["Chip_Drivers"])
        assert any(
            path and path.endswith("et_service_manifest.c") for path in group_files["Application"]
        )
        assert any(path and path.endswith("et_crc_wrap.c") for path in group_files["Wrap"])
        assert any(path and path.endswith("et_crc_service.c") for path in group_files["Services"])
        assert any(path and path.endswith("et6x_crc.c") for path in group_files["Chip_Drivers"])
        assert any(path and path.endswith("et_aes_wrap.c") for path in group_files["Wrap"])
        assert any(path and path.endswith("et_aes_service.c") for path in group_files["Services"])
        assert any(path and path.endswith("et6x_aes.c") for path in group_files["Chip_Drivers"])
        assert any(path and path.endswith("et_fmac_wrap.c") for path in group_files["Wrap"])
        assert any(path and path.endswith("et_fmac_service.c") for path in group_files["Services"])
        assert any(path and path.endswith("et6x_fmac.c") for path in group_files["Chip_Drivers"])
        assert any(path and path.endswith("et_cordic_wrap.c") for path in group_files["Wrap"])
        assert any(
            path and path.endswith("et_cordic_service.c") for path in group_files["Services"]
        )
        assert any(path and path.endswith("et6x_cordic.c") for path in group_files["Chip_Drivers"])
        assert any(path and path.endswith("et_cpu_wrap.c") for path in group_files["Wrap"])
        assert any(path and path.endswith("et_cpu_service.c") for path in group_files["Services"])
        assert any(path and path.endswith("et6x_cpu.c") for path in group_files["Chip_Drivers"])
        assert any(path and path.endswith("et_stimer_wrap.c") for path in group_files["Wrap"])
        assert any(
            path and path.endswith("et_stimer_service.c") for path in group_files["Services"]
        )
        assert any(path and path.endswith("et6x_stimer.c") for path in group_files["Chip_Drivers"])
        assert any(path and path.endswith("et_wdg_wrap.c") for path in group_files["Wrap"])
        assert any(path and path.endswith("et_wdg_service.c") for path in group_files["Services"])
        assert any(path and path.endswith("et6x_wdg.c") for path in group_files["Chip_Drivers"])
        assert any(path and path.endswith("et_spinlock_wrap.c") for path in group_files["Wrap"])
        assert any(
            path and path.endswith("et_spinlock_service.c") for path in group_files["Services"]
        )
        assert any(
            path and path.endswith("et6x_spinlock.c") for path in group_files["Chip_Drivers"]
        )
        assert not any(
            path and path.endswith("et_dma_manager.c") for path in group_files["Framework"]
        )

    expected_board_paths = {
        "ET6801_FPGA_ITCM": "boards\\et6801_fpga\\et_board_config.h",
        "ET6801_SILICON_FLASH": ("boards\\et6801_silicon\\et_board_config.h"),
        "ET6801_FPGA_MANUAL_FLASH": "boards\\et6801_fpga\\et_board_config.h",
        "ET6801_FPGA_CORE1_SMOKE_ITCM": "boards\\et6801_fpga\\et_board_config.h",
        "ET6801_SILICON_CORE1_LAUNCHER_FLASH": ("boards\\et6801_silicon\\et_board_config.h"),
    }
    expected_include_paths = {
        "ET6801_FPGA_ITCM": "boards\\et6801_fpga",
        "ET6801_SILICON_FLASH": "boards\\et6801_silicon",
        "ET6801_FPGA_MANUAL_FLASH": "boards\\et6801_fpga",
        "ET6801_FPGA_CORE1_SMOKE_ITCM": "boards\\et6801_fpga",
        "ET6801_SILICON_CORE1_LAUNCHER_FLASH": "boards\\et6801_silicon",
    }
    standard_manual_sources = {
        "et_manual_test.c",
        "et_manual_uart_test.c",
        "et_manual_crc_test.c",
        "et_manual_aes_test.c",
        "et_manual_cordic_test.c",
        "et_manual_crg_test.c",
        "et_manual_stimer_test.c",
        "et_manual_wdg_test.c",
        "et_manual_fmac_test.c",
    }
    dualcore_manual_sources = {"et_manual_test.c", "et_manual_dualcore_test.c"}
    expected_active_manual_sources = {
        "ET6801_FPGA_ITCM": set(),
        "ET6801_SILICON_FLASH": set(),
        "ET6801_FPGA_MANUAL_FLASH": standard_manual_sources,
        "ET6801_FPGA_CORE1_SMOKE_ITCM": dualcore_manual_sources,
        "ET6801_SILICON_CORE1_LAUNCHER_FLASH": dualcore_manual_sources,
    }
    for target_name, target in targets.items():
        board_group = next(
            group
            for group in target.findall("Groups/Group")
            if group.findtext("GroupName") == "Board"
        )
        board_files = board_group.findall("Files/File")
        active_board_files = [
            file.findtext("FilePath", "") for file in board_files if _keil_file_is_in_build(file)
        ]
        assert len(board_files) == 2
        assert len(active_board_files) == 1
        assert expected_board_paths[target_name] in active_board_files[0]

        manual_group = next(
            group
            for group in target.findall("Groups/Group")
            if group.findtext("GroupName") == "Manual_Diagnostics"
        )
        manual_sources = [
            file for file in manual_group.findall("Files/File") if file.findtext("FileType") == "1"
        ]
        manual_source_names = {Path(file.findtext("FilePath", "")).name for file in manual_sources}
        active_manual_source_names = {
            Path(file.findtext("FilePath", "")).name
            for file in manual_sources
            if _keil_file_is_in_build(file)
        }
        assert manual_source_names == standard_manual_sources | {"et_manual_dualcore_test.c"}
        assert active_manual_source_names == expected_active_manual_sources[target_name]

        include_path = target.findtext(
            "TargetOption/TargetArmAds/Cads/VariousControls/IncludePath",
            "",
        )
        assert expected_include_paths[target_name] in include_path
        if target_name in {"ET6801_SILICON_FLASH", "ET6801_SILICON_CORE1_LAUNCHER_FLASH"}:
            assert "boards\\et6801_fpga" not in include_path
        else:
            assert "boards\\et6801_silicon" not in include_path

        if target_name in {
            "ET6801_FPGA_MANUAL_FLASH",
            "ET6801_FPGA_CORE1_SMOKE_ITCM",
            "ET6801_SILICON_CORE1_LAUNCHER_FLASH",
        }:
            assert "manual_tests\\et6801\\include" in include_path
        else:
            assert "manual_tests\\et6801\\include" not in include_path


def test_each_wrap_calls_only_its_own_driver_family() -> None:
    wrap_source = PROJECT_ROOT / "firmware" / "wrap" / "src"
    system = (wrap_source / "et_system_wrap.c").read_text(encoding="utf-8")
    cortex = (wrap_source / "et_cortex_wrap.c").read_text(encoding="utf-8")
    crg = (wrap_source / "et_crg_wrap.c").read_text(encoding="utf-8")
    sysctrl = (wrap_source / "et_sysctrl_wrap.c").read_text(encoding="utf-8")
    irq = (wrap_source / "et_irq_wrap.c").read_text(encoding="utf-8")
    gpio = (wrap_source / "et_gpio_wrap.c").read_text(encoding="utf-8")
    uart = (wrap_source / "et_uart_wrap.c").read_text(encoding="utf-8")

    assert "SystemCoreClockUpdate" in system
    assert "SCB_EnableICache" not in system
    assert "CRG_" not in system
    assert "SYSCTRL_" not in system
    assert "AHBDMA_" not in system
    assert "UART_config(" not in system
    assert "GPIO_set" not in system
    assert "Interrupt_" not in system

    assert "SCB_EnableICache" in cortex
    assert "SystemCoreClockUpdate" not in cortex
    assert "CRG_" not in cortex
    assert "SYSCTRL_" not in cortex

    assert "CRG_enablePeripheral" in crg
    assert "CRG_resetPeripheral" in crg
    assert "SYSCTRL_" not in crg
    assert "AHBDMA_" not in crg
    assert "SCB_" not in crg

    assert "SYSCTRL_configDMAMux" in sysctrl
    assert "SYSCTRL_freeDMAMuxInterface" in sysctrl
    assert "CRG_" not in sysctrl
    assert "SCB_" not in sysctrl

    assert "Interrupt_initVectorTable" in irq
    assert "NVIC_SetPriority" in irq
    assert "UART_config(" not in irq
    assert "UART_get" not in irq
    assert "GPIO_set" not in irq
    assert "SystemCoreClock" not in irq

    assert "GPIO_setPadConfig" in gpio
    assert "GPIO_setPinConfig" in gpio
    assert "UART_config(" not in gpio
    assert "UART_get" not in gpio
    assert "Interrupt_" not in gpio
    assert "NVIC_" not in gpio

    assert "UART_config" in uart
    assert "UART_testGetInterruptSnapshot" in uart
    assert "GPIO_set" not in uart
    assert "Interrupt_" not in uart
    assert "NVIC_" not in uart
    assert "SystemCoreClock" not in uart


def test_generated_keil_project_matches_generation_record() -> None:
    project = GENERATED_FIRMWARE_PROJECT
    record_path = project.with_suffix(".generation.json")
    record = json.loads(record_path.read_text(encoding="utf-8"))

    assert Path(record["output"]).resolve() == project.resolve()
    assert hashlib.sha256(project.read_bytes()).hexdigest() == record["sha256"]
    jlink_settings = project.parent / "JLinkSettings.ini"
    jlink_record = record["support_files"]["jlink_settings"]
    assert Path(jlink_record["output"]).resolve() == jlink_settings.resolve()
    assert hashlib.sha256(jlink_settings.read_bytes()).hexdigest() == jlink_record["sha256"]
    settings_text = jlink_settings.read_text(encoding="utf-8")
    assert "Override = 1" in settings_text
    assert 'Device="Cortex-M7"' in settings_text
    options = project.with_suffix(".uvoptx")
    options_record = record["support_files"]["keil_options"]
    assert Path(options_record["output"]).resolve() == options.resolve()
    assert hashlib.sha256(options.read_bytes()).hexdigest() == options_record["sha256"]
    options_root = ET.parse(options).getroot()
    option_targets = {
        target.findtext("TargetName"): target for target in options_root.findall("Target")
    }
    flash_options = option_targets["ET6801_SILICON_FLASH"]
    assert flash_options.findtext("TargetOption/DebugOpt/pMon") == r"Segger\JL2CM3.dll"
    assert flash_options.find("TargetOption/DebugDescription") is None


def test_keil_manifest_is_machine_path_independent() -> None:
    manifest = (PROJECT_ROOT / "firmware" / "chips" / "et6801" / "project.yaml").read_text(
        encoding="utf-8"
    )

    assert "D:/" not in manifest
    assert "C:/" not in manifest
    assert "template_root: manifest" in manifest
    assert "sdk_environment:" not in manifest
    assert "sdk_groups:" not in manifest
    assert "sdk_includes:" not in manifest


def test_generated_keil_project_uses_only_firmware_source_files() -> None:
    firmware_root = (PROJECT_ROOT / "firmware").resolve()
    project = GENERATED_FIRMWARE_PROJECT
    project_root = ET.parse(project).getroot()

    for target in project_root.findall("Targets/Target"):
        for file_node in target.findall("Groups/Group/Files/File"):
            source = (project.parent / file_node.findtext("FilePath", "")).resolve()
            assert source.is_relative_to(firmware_root), source
            assert source.is_file(), source

        include_text = target.findtext(
            "TargetOption/TargetArmAds/Cads/VariousControls/IncludePath",
            "",
        )
        for include in filter(None, include_text.split(";")):
            include_path = (project.parent / include).resolve()
            assert include_path.is_relative_to(firmware_root), include_path
            assert include_path.is_dir(), include_path

    record = json.loads(project.with_suffix(".generation.json").read_text(encoding="utf-8"))
    assert record["sdk_root"] is None
    assert Path(record["template"]).resolve().is_relative_to(firmware_root)
    assert Path(record["template_root"]).resolve().is_relative_to(firmware_root)


def _write_minimal_generated_flash_project(
    tmp_path: Path,
) -> tuple[Path, Path]:
    project = tmp_path / "ET6801_Automated_Test.uvprojx"
    image = tmp_path / "Objects" / "SILICON_FLASH" / "et6801_test_silicon.axf"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"test-axf")
    jlink_settings = tmp_path / "JLinkSettings.ini"
    jlink_settings.write_text(
        '[FLASH]\nOverride = 1\nDevice="Cortex-M7"\n',
        encoding="utf-8",
    )
    options = tmp_path / "ET6801_Automated_Test.uvoptx"
    options.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<ProjectOpt>
  <Target>
    <TargetName>ET6801_SILICON_FLASH</TargetName>
    <TargetOption>
      <TargetDriverDllRegistry>
        <SetRegEntry>
          <Key>DLGUARM</Key><Name>d</Name>
        </SetRegEntry>
        <SetRegEntry>
          <Key>JL2CM3</Key><Name>-U4294967295 -S2 -FN1 -FF0ET6801.FLM -FS08000000 -FL080000 -FP0($$Device:ET6801$Flash\\ET6801.FLM)</Name>
        </SetRegEntry>
        <SetRegEntry>
          <Key>UL2CM3</Key><Name>UL2CM3(-FN1 -FF0ET6801 -FS08000000 -FL080000 -FP0($$Device:ET6801$Flash\\ET6801.FLM))</Name>
        </SetRegEntry>
      </TargetDriverDllRegistry>
      <DebugOpt><pMon>Segger\\JL2CM3.dll</pMon></DebugOpt>
    </TargetOption>
  </Target>
</ProjectOpt>
""",
        encoding="utf-8",
    )
    project.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<Project>
  <Targets>
    <Target>
      <TargetName>ET6801_SILICON_FLASH</TargetName>
      <TargetOption>
        <TargetCommonOption>
          <Device>ET6801</Device>
          <Vendor>ETMCU</Vendor>
          <PackID>ETMCU.ET6801_DFP.0.1.0</PackID>
          <Cpu>IRAM(0x20000000,0x20000) IROM(0x08000000,0x80000) CPUTYPE("Cortex-M7")</Cpu>
          <RegisterFile>$$Device:ET6801$Device\\Include\\et6801.h</RegisterFile>
          <FlashDriverDll>UL2CM3(-FN1 -FF0ET6801 -FS08000000 -FL080000 -FP0($$Device:ET6801$Flash\\ET6801.FLM))</FlashDriverDll>
          <TargetStatus><InvalidFlash>0</InvalidFlash></TargetStatus>
          <OutputDirectory>.\\Objects\\SILICON_FLASH\\</OutputDirectory>
          <OutputName>et6801_test_silicon</OutputName>
        </TargetCommonOption>
        <Utilities>
          <Flash1><UpdateFlashBeforeDebugging>1</UpdateFlashBeforeDebugging></Flash1>
        </Utilities>
      </TargetOption>
    </Target>
  </Targets>
</Project>
""",
        encoding="utf-8",
    )
    record = {
        "schema_version": 1,
        "output": str(project.resolve()),
        "sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
        "support_files": {
            "jlink_settings": {
                "output": str(jlink_settings.resolve()),
                "sha256": hashlib.sha256(jlink_settings.read_bytes()).hexdigest(),
            },
            "keil_options": {
                "output": str(options.resolve()),
                "sha256": hashlib.sha256(options.read_bytes()).hexdigest(),
            },
        },
    }
    project.with_suffix(".generation.json").write_text(
        json.dumps(record),
        encoding="utf-8",
    )
    return project, image


def _run_flash_prepare(
    project: Path,
    image: Path | None = None,
    jlink_serial: str | None = None,
) -> subprocess.CompletedProcess[str]:
    powershell = shutil.which("powershell.exe")
    if powershell is None:
        pytest.skip("PowerShell is required for the firmware Flash preflight")
    script = PROJECT_ROOT / "tools" / "firmware" / "flash_and_run_et6801_firmware.ps1"
    command = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Project",
        str(project),
        "-PrepareOnly",
    ]
    if image is not None:
        command.extend(["-Image", str(image)])
    if jlink_serial is not None:
        command.extend(["-JLinkSerial", jlink_serial])

    # 环境：单测直接启动Windows PowerShell，显式使用其系统模块目录，避免继承Agent/Pwsh模块路径。
    environment = dict(os.environ)
    windows_root = environment.get("WINDIR", r"C:\Windows")
    environment["PSModulePath"] = str(
        Path(windows_root, "System32", "WindowsPowerShell", "v1.0", "Modules")
    )

    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_flash_prepare_binds_evidence_to_keil_target_image(
    tmp_path: Path,
) -> None:
    project, image = _write_minimal_generated_flash_project(tmp_path)

    accepted = _run_flash_prepare(project, image)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    assert "Image_SHA256" in accepted.stdout
    assert hashlib.sha256(image.read_bytes()).hexdigest().upper() in (accepted.stdout)

    other_image = tmp_path / "other.axf"
    other_image.write_bytes(b"other")
    rejected = _run_flash_prepare(project, other_image)
    assert rejected.returncode != 0
    assert "Image mismatch" in rejected.stdout + rejected.stderr


def test_flash_prepare_rejects_generated_project_drift(
    tmp_path: Path,
) -> None:
    project, _ = _write_minimal_generated_flash_project(tmp_path)
    project.write_text(
        project.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    rejected = _run_flash_prepare(project)
    assert rejected.returncode != 0
    assert "project drift detected" in (rejected.stdout + rejected.stderr).lower()


# 验证J-Link自动选择序列号的有符号和无符号表示属于同一语义。
def test_flash_prepare_accepts_jlink_auto_select_sentinel(
    tmp_path: Path,
) -> None:
    project, _ = _write_minimal_generated_flash_project(tmp_path)

    accepted = _run_flash_prepare(project, jlink_serial="-1")
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr


# 验证具体探针序列号不匹配时仍然失败关闭。
def test_flash_prepare_rejects_different_jlink_serial(
    tmp_path: Path,
) -> None:
    project, _ = _write_minimal_generated_flash_project(tmp_path)

    rejected = _run_flash_prepare(project, jlink_serial="123456")
    assert rejected.returncode != 0
    assert "J-Link serial mismatch" in rejected.stdout + rejected.stderr


def test_flash_prepare_rejects_missing_jlink_settings(
    tmp_path: Path,
) -> None:
    project, _ = _write_minimal_generated_flash_project(tmp_path)
    (tmp_path / "JLinkSettings.ini").unlink()

    rejected = _run_flash_prepare(project)
    assert rejected.returncode != 0
    assert "J-Link settings are missing" in (rejected.stdout + rejected.stderr)
