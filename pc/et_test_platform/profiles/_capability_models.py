# 芯片Capability的稳定只读数据模型与查询接口。
#
# 职责：承载已解析的Capability/Audit事实，并提供不执行设备I/O的强类型查询。
# 边界：不读取YAML、不定位打包资源、不执行Schema解析，也不访问Bench、Driver或Target。
# 依赖：仅依赖标准库和平台Capability异常。

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ..core.errors import (
    CapabilityLookupError,
    ConfigurationError,
    UnsupportedCapability,
)

_SEMANTIC_NAME = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
_CAPABILITY_ID = re.compile(
    r"^[a-z][a-z0-9_]*\.(feature|limit|option|interrupt|identity|parameter)"
    r"(?:\.[a-z][a-z0-9_]*)+$"
)
_V2_CAPABILITY_KEYS = {
    "features",
    "limits",
    "options",
    "parameters",
    "interrupts",
    "identities",
}


def _capability_kind(capability_id: str) -> str:
    if not isinstance(capability_id, str) or not _CAPABILITY_ID.fullmatch(capability_id):
        raise CapabilityLookupError(f"invalid capability ID {capability_id!r}")
    return capability_id.split(".", 2)[1]


# 表示 InterruptCapability 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True)
class InterruptCapability:
    svd_name: str
    irqn: int


# 表示 CapabilityEvidence 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True)
class CapabilityEvidence:
    instance: str
    kind: str
    path: str
    rule: str
    member: str | None = None


# 表示 UnclassifiedFact 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True)
class UnclassifiedFact:
    instance: str
    kind: str
    path: str
    reason: str


# 表示 CapabilityAudit 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True)
class CapabilityAudit:
    chip_id: str
    ip_id: str
    source: Mapping[str, Any]
    unclassified: tuple[UnclassifiedFact, ...]


# 表示 CapabilityProfile 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True)
class CapabilityProfile:
    chip_id: str
    ip_id: str
    schema: str
    source: Mapping[str, Any]
    _instances: Mapping[str, Mapping[str, str]]
    _capabilities: Mapping[str, Any]
    _evidence: Mapping[str, tuple[CapabilityEvidence, ...]]

    # 查询或构造 instances 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    @property
    def instances(self) -> tuple[str, ...]:

        return tuple(self._instances)

    # 查询或构造 capability ids 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    @property
    def capability_ids(self) -> tuple[str, ...]:

        return tuple(self._capabilities)

    # 查询或构造 supporting instances 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def supporting_instances(self, capability_id: str) -> tuple[str, ...]:

        self._require_kind(capability_id, "feature")
        value = self._capabilities.get(capability_id)
        if value is None:
            return ()
        return value

    # 查询或构造 supports 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def supports(self, capability_id: str, *, instance: str) -> bool:

        self._require_instance(instance)
        return instance in self.supporting_instances(capability_id)

    # 查询或构造 require 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def require(self, capability_id: str, *, instance: str) -> None:

        if not self.supports(capability_id, instance=instance):
            raise UnsupportedCapability(
                f"{self.chip_id}.{instance} does not support {capability_id}"
            )

    # 查询或构造 value 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def value(self, capability_id: str, *, instance: str) -> Any:

        self._require_instance(instance)
        if not capability_id.startswith(f"{self.ip_id}."):
            raise CapabilityLookupError(f"{capability_id!r} does not belong to IP {self.ip_id!r}")
        kind = _capability_kind(capability_id)
        if kind == "feature":
            raise CapabilityLookupError(f"{capability_id!r} is a feature; use supports()")
        value_by_instance = self._capabilities.get(capability_id)
        if value_by_instance is None or instance not in value_by_instance:
            raise CapabilityLookupError(f"{capability_id!r} has no value for instance {instance!r}")
        return value_by_instance[instance]

    # 查询或构造 has feature 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def has_feature(self, name: str, *, instance: str) -> bool:

        return self.supports(
            self._semantic_id("feature", name),
            instance=instance,
        )

    # 查询或构造 limit 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def limit(self, name: str, *, instance: str) -> int | float:

        return self.value(
            self._semantic_id("limit", name),
            instance=instance,
        )

    # 查询或构造 options 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def options(self, name: str, *, instance: str) -> tuple[Any, ...]:

        return self.value(
            self._semantic_id("option", name),
            instance=instance,
        )

    # 查询或构造 interrupt 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def interrupt(
        self,
        name: str,
        *,
        instance: str,
    ) -> InterruptCapability:

        value = self.value(
            self._semantic_id("interrupt", name),
            instance=instance,
        )
        if not isinstance(value, InterruptCapability):
            raise CapabilityLookupError(f"{name!r} is not a structured interrupt capability")
        return value

    # 查询或构造 identity 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def identity(self, name: str, *, instance: str) -> str | int:

        return self.value(
            self._semantic_id("identity", name),
            instance=instance,
        )

    # 查询或构造 parameter 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def parameter(
        self,
        name: str,
        *,
        instance: str,
        member: str = "instance",
    ) -> str | int | float | bool:

        values = self.value(
            self._semantic_id("parameter", name),
            instance=instance,
        )
        if not isinstance(member, str) or not _SEMANTIC_NAME.fullmatch(member):
            raise CapabilityLookupError(f"parameter member {member!r} is invalid")
        member_id = member
        if not isinstance(values, Mapping) or member_id not in values:
            raise CapabilityLookupError(
                f"parameter {name!r} has no member {member_id!r} for instance {instance!r}"
            )
        return values[member_id]

    # 查询或构造 parameter members 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def parameter_members(
        self,
        name: str,
        *,
        instance: str,
    ) -> tuple[str, ...]:

        values = self.value(
            self._semantic_id("parameter", name),
            instance=instance,
        )
        if not isinstance(values, Mapping):
            raise CapabilityLookupError(f"{name!r} is not a parameter")
        return tuple(values)

    # 查询或构造 evidence 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def evidence(
        self,
        kind: str,
        name: str,
        *,
        instance: str | None = None,
        member: str | None = None,
    ) -> tuple[CapabilityEvidence, ...]:

        capability_id = self._semantic_id(kind, name)
        items = self._evidence.get(capability_id, ())
        if member is not None and instance is None:
            raise CapabilityLookupError("member-scoped evidence requires an instance")
        if instance is None:
            return items
        self._require_instance(instance)
        selected = tuple(item for item in items if item.instance == instance)
        if member is None:
            return selected
        if not isinstance(member, str) or not _SEMANTIC_NAME.fullmatch(member):
            raise CapabilityLookupError(f"evidence member {member!r} is invalid")
        member_id = member
        return tuple(item for item in selected if item.member == member_id)

    # 查询或构造 select instances 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def select_instances(self, instances: Iterable[str]) -> CapabilityProfile:

        selected = tuple(instances)
        unknown = set(selected) - set(self._instances)
        if unknown:
            raise ConfigurationError(
                f"{self.ip_id} runtime registry contains unknown instances: "
                + ", ".join(sorted(unknown))
            )
        selected_set = set(selected)
        capabilities: dict[str, Any] = {}
        for capability_id, value in self._capabilities.items():
            if _capability_kind(capability_id) == "feature":
                capabilities[capability_id] = tuple(
                    instance for instance in value if instance in selected_set
                )
            else:
                capabilities[capability_id] = MappingProxyType(
                    {instance: item for instance, item in value.items() if instance in selected_set}
                )
        evidence = {
            capability_id: tuple(item for item in items if item.instance in selected_set)
            for capability_id, items in self._evidence.items()
        }
        return CapabilityProfile(
            chip_id=self.chip_id,
            ip_id=self.ip_id,
            schema=self.schema,
            source=self.source,
            _instances=MappingProxyType(
                {instance: self._instances[instance] for instance in selected}
            ),
            _capabilities=MappingProxyType(capabilities),
            _evidence=MappingProxyType(evidence),
        )

    def _semantic_id(self, kind: str, name: str) -> str:
        if kind not in _V2_CAPABILITY_KEYS and kind not in {
            "feature",
            "limit",
            "option",
            "interrupt",
            "identity",
            "parameter",
        }:
            raise CapabilityLookupError(f"unknown capability kind {kind!r}")
        singular = {
            "features": "feature",
            "limits": "limit",
            "options": "option",
            "interrupts": "interrupt",
            "identities": "identity",
            "parameters": "parameter",
        }.get(kind, kind)
        if not isinstance(name, str) or not _SEMANTIC_NAME.fullmatch(name):
            raise CapabilityLookupError(f"semantic capability name {name!r} is invalid")
        return f"{self.ip_id}.{singular}.{name}"

    def _require_kind(self, capability_id: str, expected: str) -> None:
        kind = _capability_kind(capability_id)
        if not capability_id.startswith(f"{self.ip_id}."):
            raise CapabilityLookupError(f"{capability_id!r} does not belong to IP {self.ip_id!r}")
        if kind != expected:
            raise CapabilityLookupError(f"{capability_id!r} is {kind!r}, expected {expected!r}")

    def _require_instance(self, instance: str) -> None:
        if instance not in self._instances:
            raise CapabilityLookupError(f"unknown {self.ip_id} instance {instance!r}")


# 表示 ChipCapabilities 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True)
class ChipCapabilities:
    chip_id: str
    schema: str
    _profiles: Mapping[str, CapabilityProfile]

    # 查询或构造 ip ids 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    @property
    def ip_ids(self) -> tuple[str, ...]:

        return tuple(self._profiles)

    # 查询或构造 instances 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def instances(self, ip_id: str) -> tuple[str, ...]:

        return self._require_ip(ip_id).instances

    # 查询或构造 select instances 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def select_instances(
        self,
        available: Mapping[str, Iterable[str]],
    ) -> ChipCapabilities:

        unknown_ips = set(available) - set(self._profiles)
        if unknown_ips:
            raise ConfigurationError(
                "runtime registry contains IPs absent from the chip profile: "
                + ", ".join(sorted(unknown_ips))
            )
        profiles = {
            ip_id: profile.select_instances(available[ip_id])
            for ip_id, profile in self._profiles.items()
            if ip_id in available
        }
        return ChipCapabilities(
            chip_id=self.chip_id,
            schema=self.schema,
            _profiles=MappingProxyType(profiles),
        )

    # 查询或构造 supporting instances 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def supporting_instances(self, capability_id: str) -> tuple[str, ...]:

        return self._profile_for(capability_id).supporting_instances(capability_id)

    # 查询或构造 supports 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def supports(self, capability_id: str, *, instance: str) -> bool:

        return self._profile_for(capability_id).supports(
            capability_id,
            instance=instance,
        )

    # 查询或构造 require 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def require(self, capability_id: str, *, instance: str) -> None:

        self._profile_for(capability_id).require(
            capability_id,
            instance=instance,
        )

    # 查询或构造 value 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def value(self, capability_id: str, *, instance: str) -> Any:

        return self._profile_for(capability_id).value(
            capability_id,
            instance=instance,
        )

    # 查询或构造 has feature 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def has_feature(
        self,
        ip_id: str,
        name: str,
        *,
        instance: str,
    ) -> bool:

        return self._require_ip(ip_id).has_feature(name, instance=instance)

    # 查询或构造 limit 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def limit(self, ip_id: str, name: str, *, instance: str) -> int | float:

        return self._require_ip(ip_id).limit(name, instance=instance)

    # 查询或构造 options 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def options(
        self,
        ip_id: str,
        name: str,
        *,
        instance: str,
    ) -> tuple[Any, ...]:

        return self._require_ip(ip_id).options(name, instance=instance)

    # 查询或构造 interrupt 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def interrupt(
        self,
        ip_id: str,
        name: str,
        *,
        instance: str,
    ) -> InterruptCapability:

        return self._require_ip(ip_id).interrupt(name, instance=instance)

    # 查询或构造 identity 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def identity(
        self,
        ip_id: str,
        name: str,
        *,
        instance: str,
    ) -> str | int:

        return self._require_ip(ip_id).identity(name, instance=instance)

    # 查询或构造 parameter 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def parameter(
        self,
        ip_id: str,
        name: str,
        *,
        instance: str,
        member: str = "instance",
    ) -> str | int | float | bool:

        return self._require_ip(ip_id).parameter(
            name,
            instance=instance,
            member=member,
        )

    # 查询或构造 parameter members 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def parameter_members(
        self,
        ip_id: str,
        name: str,
        *,
        instance: str,
    ) -> tuple[str, ...]:

        return self._require_ip(ip_id).parameter_members(
            name,
            instance=instance,
        )

    # 查询或构造 evidence 对应的 Capability 事实；不执行硬件 I/O，缺失或冲突事实以明确异常报告。
    def evidence(
        self,
        ip_id: str,
        kind: str,
        name: str,
        *,
        instance: str | None = None,
        member: str | None = None,
    ) -> tuple[CapabilityEvidence, ...]:

        return self._require_ip(ip_id).evidence(
            kind,
            name,
            instance=instance,
            member=member,
        )

    def _profile_for(self, capability_id: str) -> CapabilityProfile:
        _capability_kind(capability_id)
        return self._require_ip(capability_id.split(".", 1)[0])

    def _require_ip(self, ip_id: str) -> CapabilityProfile:
        profile = self._profiles.get(ip_id)
        if profile is None:
            raise CapabilityLookupError(
                f"chip {self.chip_id!r} has no capability profile for IP {ip_id!r}"
            )
        return profile
