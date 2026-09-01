# AES 正式测试用例 Support。
#
# 职责：准备静态/运行时门禁与不可变 AES、Resource Driver 引用。
# 边界：不修改 Feature，不隐藏完整 Case 流程、跨 IP 顺序或最终断言。
# 依赖：pytest、AES Driver、Resource Driver 和 ChipCapabilities。

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from ...core.errors import CapabilityLookupError, UnsupportedCapability
from ...drivers.aes import (
    AES_SERVICE_ID,
    AesCapabilities,
    AesConfig,
    AesDirection,
    AesDmaTransferMode,
    AesDriver,
    AesFeature,
    AesIrqEvent,
    AesKeySize,
    AesMode,
    AesPadding,
)
from ...drivers.dma import DMA_SERVICE_ID, DmaDriver
from ...drivers.resource import ResourceDriver
from ...drivers.sysctrl import SYSCTRL_SERVICE_ID, SysctrlDriver
from ...profiles.capabilities import ChipCapabilities
from ...profiles.resolvers.dma_routes import AesDmaRoute


@dataclass(frozen=True, slots=True)
class AesCaseSupport:
    instance_id: int
    instance_name: str
    aes: AesDriver
    resource: ResourceDriver
    runtime: AesCapabilities


@dataclass(frozen=True, slots=True)
class AesDmaCaseSupport:
    # 保存 P2/P3 显式编排所需的 AES、DMA 和 SYSCTRL 单 IP Driver。

    aes_support: AesCaseSupport
    dma: DmaDriver
    sysctrl: SysctrlDriver
    route: AesDmaRoute


AesSupportFactory = Callable[[int], AesCaseSupport]


def require_aes_static_capability(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
    require_semantic: bool = False,
) -> str:
    instance = f"aes{instance_id}"
    try:
        if instance not in capabilities.instances("aes"):
            raise UnsupportedCapability(f"AES instance {instance!r} is unavailable")
        identity = capabilities.identity("aes", "base_address", instance=instance)
        if identity in (None, ""):
            raise UnsupportedCapability("AES base address identity is unavailable")
        irq = capabilities.interrupt("aes", "irq", instance=instance).irqn
        if isinstance(irq, bool) or not isinstance(irq, int) or irq < 0:
            raise UnsupportedCapability("AES IRQ identity is unavailable")
        if require_semantic and not capabilities.supporting_instances("aes.feature.encryption"):
            raise UnsupportedCapability("AES semantic feature mapping is not declared")
        return instance
    except (CapabilityLookupError, UnsupportedCapability) as exc:
        raise UnsupportedCapability(f"AES static capability gap: {exc}") from exc


def require_aes_runtime_capability(runtime: AesCapabilities, *, require_feature: int = 0) -> None:
    if runtime.api_version != 1 or runtime.block_size_bytes != 16:
        raise UnsupportedCapability("AES runtime capability version/block size is incompatible")
    if runtime.max_process_bytes <= 0 or runtime.max_process_bytes > 4096:
        raise UnsupportedCapability("AES runtime process limit is outside the V1 bound")
    if require_feature and int(runtime.features) & require_feature != require_feature:
        raise UnsupportedCapability("AES runtime feature bits are incomplete")


def require_aes_config_supported(support: AesCaseSupport, config: AesConfig) -> None:
    # Case 只声明自己需要的稳定 AES 语义，不根据 chip_id 建立私有分支。
    feature = AesFeature.MODULE_ENABLE
    feature |= (
        AesFeature.ENCRYPTION if config.direction is AesDirection.ENCRYPT else AesFeature.DECRYPTION
    )
    feature |= AesFeature.KEY_128 if config.key_size is AesKeySize.AES128 else AesFeature.KEY_256
    feature |= {
        AesMode.ECB: AesFeature.ECB,
        AesMode.CBC: AesFeature.CBC | AesFeature.IV,
        AesMode.CTR: AesFeature.CTR | AesFeature.IV | AesFeature.CTR_COUNTER,
    }[config.mode]
    if config.padding is not AesPadding.NONE:
        feature |= AesFeature.PADDING
    runtime = support.runtime
    option_checks = (
        (runtime.key_size_mask, config.key_size, "key size"),
        (runtime.mode_mask, config.mode, "mode"),
        (runtime.padding_mask, config.padding, "padding"),
        (runtime.endian_mask, config.endian, "endian"),
        (runtime.dma_mode_mask, config.dma_transfer_mode, "DMA mode"),
    )
    try:
        require_aes_runtime_capability(runtime, require_feature=int(feature))
        for option_mask, option, label in option_checks:
            if option_mask & (1 << int(option)) == 0:
                raise UnsupportedCapability(f"AES runtime {label} option is unavailable")
    except UnsupportedCapability as error:
        pytest.skip(f"skip_by_runtime_feature: {error}")


def require_aes_features_supported(
    support: AesCaseSupport,
    features: AesFeature,
) -> None:
    # 非配置型 Feature 使用同一运行时能力事实，不允许 Case 猜测芯片实现。
    try:
        require_aes_runtime_capability(
            support.runtime,
            require_feature=int(features),
        )
    except UnsupportedCapability as error:
        pytest.skip(f"skip_by_runtime_feature: {error}")


def require_aes_irq_supported(
    support: AesCaseSupport,
    event: AesIrqEvent,
    *,
    require_transfer: bool = False,
) -> None:
    # IRQ Case 按运行时事件交集门禁，缺失事件不能被轮询路径伪装成 PASS。
    try:
        require_aes_runtime_capability(
            support.runtime,
            require_feature=int(AesFeature.INTERRUPTS | AesFeature.TEST_EXTENSIONS),
        )
        if event & ~support.runtime.irq_event_mask:
            raise UnsupportedCapability("AES runtime IRQ event is unavailable")
        if require_transfer and not support.runtime.irq_transfer_supported:
            raise UnsupportedCapability("AES runtime IRQ transfer is unavailable")
    except UnsupportedCapability as error:
        pytest.skip(f"skip_by_runtime_feature: {error}")


def require_aes_dma_supported(
    support: AesCaseSupport,
    transfer_mode: AesDmaTransferMode,
) -> None:
    # DMA Case 同时要求 AES DMA Feature 与选中的 FIFO/REGISTER mode。
    try:
        required = AesFeature.DMA
        if transfer_mode is AesDmaTransferMode.FIFO:
            required |= AesFeature.DMA_FIFO_PATH
        require_aes_runtime_capability(support.runtime, require_feature=int(required))
        if support.runtime.dma_mode_mask & (1 << int(transfer_mode)) == 0:
            raise UnsupportedCapability("AES runtime DMA mode is unavailable")
    except UnsupportedCapability as error:
        pytest.skip(f"skip_by_runtime_feature: {error}")


def require_aes_data_length_bits(support: AesCaseSupport, minimum_bits: int) -> None:
    # 长度边界来自运行时能力，Case 不写入某颗芯片固定的数据长度位宽。
    if support.runtime.hardware_data_length_bits < minimum_bits:
        pytest.skip(
            "skip_by_runtime_feature: AES data length width "
            f"{support.runtime.hardware_data_length_bits} is below {minimum_bits} bits"
        )


def aes_support_for(
    framework_communication,
    target_capabilities: ChipCapabilities,
    resource_driver: ResourceDriver,
) -> AesSupportFactory:
    services = framework_communication.runtime_services

    def build(instance_id: int) -> AesCaseSupport:
        require_aes_static_capability(target_capabilities, instance_id=instance_id)
        if not any(
            item.service_id == AES_SERVICE_ID and item.instance_id == instance_id
            for item in services
        ):
            pytest.skip(
                f"skip_by_runtime_service: AES service 0x{AES_SERVICE_ID:04x} "
                f"instance {instance_id} is not registered"
            )
        driver = AesDriver(framework_communication.target_client, instance_id=instance_id)
        runtime = driver.capabilities_get()
        try:
            require_aes_runtime_capability(runtime)
        except UnsupportedCapability as error:
            pytest.skip(f"skip_by_runtime_feature: {error}")
        return AesCaseSupport(
            instance_id=instance_id,
            instance_name=f"aes{instance_id}",
            aes=driver,
            resource=resource_driver,
            runtime=runtime,
        )

    return build


def build_aes_dma_support(
    framework_communication,
    target_capabilities: ChipCapabilities,
    resource_driver: ResourceDriver,
    aes_support_factory: AesSupportFactory,
    instance_id: int,
    route: AesDmaRoute,
) -> AesDmaCaseSupport:
    # 仅在 Service 已注册后构造跨 IP Driver，不执行任何硬件动作。

    services = framework_communication.runtime_services
    for service_id, label in (
        (DMA_SERVICE_ID, "DMA"),
        (SYSCTRL_SERVICE_ID, "SYSCTRL"),
    ):
        if not any(item.service_id == service_id for item in services):
            pytest.skip(f"skip_by_runtime_service: {label} service is not registered")
    aes_support = aes_support_factory(instance_id)
    target = framework_communication.target_client
    dma = DmaDriver(target, instance_id=route.controller)
    sysctrl = SysctrlDriver(target)
    return AesDmaCaseSupport(
        aes_support=aes_support,
        dma=dma,
        sysctrl=sysctrl,
        route=route,
    )
