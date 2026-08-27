# Deterministic quality review for generated Capability v2 artifacts.

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable, Mapping

from svd_fact_ir import IpGroup, SvdFactIR
from svd_semantics import (
    CONFIGURABLE_OPTION_ACCESS,
    SemanticArtifacts,
    explicit_field_markers,
    has_dominant_short_tokens,
    opaque_short_tokens,
)


QUALITY_SCHEMA = "et-capability-quality/v1"
_SECTIONS = {
    "feature": "features",
    "limit": "limits",
    "option": "options",
    "parameter": "parameters",
    "interrupt": "interrupts",
    "identity": "identities",
}
_CAPABILITY_ID = re.compile(
    r"^[a-z][a-z0-9_]*\.(feature|limit|option|parameter|interrupt|identity)"
    r"\.[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$"
)
_GENERIC_NAMES = {
    "config",
    "control",
    "data",
    "enable",
    "status",
    "unknown",
    "value",
}
_NUMERIC_TOKEN = re.compile(r"\d+")


# Return one canonical, chip-independent quality report document.
def analyze(
    artifacts: SemanticArtifacts,
    *,
    facts: SvdFactIR | None = None,
    required_capabilities: Iterable[str] = (),
) -> dict[str, Any]:

    profile_ids = tuple(sorted(artifacts.profiles))
    if profile_ids != tuple(sorted(artifacts.audits)):
        missing_profiles = sorted(set(artifacts.audits) - set(profile_ids))
        missing_audits = sorted(set(profile_ids) - set(artifacts.audits))
        raise ValueError(
            "profile/audit IP mismatch: "
            f"missing_profiles={missing_profiles}, missing_audits={missing_audits}"
        )
    if not profile_ids:
        raise ValueError("quality analysis requires at least one profile")

    first = artifacts.profiles[profile_ids[0]]
    chip_id = str(first["chip"])
    source = dict(first["source"])
    fact_groups = _validated_fact_groups(facts, profile_ids, source)
    issues: list[dict[str, str]] = []
    per_ip: dict[str, Any] = {}
    totals = _empty_counts()

    for ip_id in profile_ids:
        profile = artifacts.profiles[ip_id]
        audit = artifacts.audits[ip_id]
        if profile["chip"] != chip_id or audit["chip"] != chip_id:
            raise ValueError(f"chip mismatch in {ip_id}")
        if profile["source"] != source or audit["source"] != source:
            raise ValueError(f"source mismatch in {ip_id}")

        capabilities = profile["capabilities"]
        field_details = _field_details(fact_groups.get(ip_id))
        audit_reason_counts = dict(
            sorted(Counter(item["reason"] for item in audit["unclassified"]).items())
        )
        semantic_candidates = _semantic_candidates(
            fact_groups.get(ip_id),
            audit["unclassified"],
        )
        semantic_candidate_conflicts = _semantic_candidate_value_conflicts(semantic_candidates)
        identity_surface = _identity_only_surface(fact_groups.get(ip_id))
        parameter_domain_conflicts = _parameter_domain_conflicts(
            fact_groups.get(ip_id),
            profile,
        )
        candidate_group_counts = dict(
            sorted(Counter(item["kind"] for item in semantic_candidates).items())
        )
        candidate_fact_counts = {
            kind: sum(
                candidate["occurrence_count"]
                for candidate in semantic_candidates
                if candidate["kind"] == kind
            )
            for kind in sorted(candidate_group_counts)
        }
        counts = {
            "instances": len(profile["instances"]),
            "capability_definitions": 0,
            "capability_values": 0,
            "evidence_entries": sum(len(items) for items in profile["evidence"].values()),
            "classified_facts": 0,
            "unclassified_facts": len(audit["unclassified"]),
            "semantic_candidate_groups": len(semantic_candidates),
            "semantic_candidate_facts": sum(
                item["occurrence_count"] for item in semantic_candidates
            ),
            "semantic_candidate_conflicts": len(semantic_candidate_conflicts),
            "parameter_domain_conflicts": len(parameter_domain_conflicts),
        }
        category_counts: dict[str, int] = {}
        names_by_kind: dict[str, set[str]] = {}
        capability_ids: list[str] = []

        for kind, section in _SECTIONS.items():
            values = capabilities[section]
            category_counts[section] = len(values)
            counts["capability_definitions"] += len(values)
            names_by_kind[kind] = set(values)
            for name, value in values.items():
                if kind == "parameter":
                    counts["capability_values"] += sum(len(members) for members in value.values())
                else:
                    counts["capability_values"] += len(value)
                capability_id = f"{ip_id}.{kind}.{name}"
                capability_ids.append(capability_id)
                issues.extend(_name_issues(capability_id, name))
                if kind == "feature":
                    issues.extend(
                        _feature_evidence_issues(
                            capability_id,
                            profile["evidence"].get(capability_id, ()),
                            field_details,
                            ip_id=ip_id,
                        )
                    )
                elif kind in {"limit", "option"}:
                    issues.extend(
                        _configurable_value_issues(
                            capability_id,
                            profile["evidence"].get(capability_id, ()),
                            field_details,
                            ip_id=ip_id,
                        )
                    )
                elif kind == "parameter":
                    issues.extend(
                        _parameter_evidence_issues(
                            capability_id,
                            profile["evidence"].get(capability_id, ()),
                            field_details,
                            ip_id=ip_id,
                        )
                    )

        for name in sorted(set().union(*names_by_kind.values())):
            kinds = sorted(kind for kind, names in names_by_kind.items() if name in names)
            if len(kinds) > 1 and not _is_expected_cross_kind_name(kinds):
                issues.append(
                    _issue(
                        "warning",
                        "cross_kind_name_collision",
                        ip=ip_id,
                        capability=name,
                        detail="same name appears in kinds: " + ",".join(kinds),
                    )
                )

        classifications: dict[tuple[str, str, str], set[str]] = {}
        for capability_id, values in profile["evidence"].items():
            for item in values:
                fact = (item["instance"], item["kind"], item["path"])
                classifications.setdefault(fact, set()).add(capability_id)
        for (instance, kind, path), capability_ids_for_fact in sorted(classifications.items()):
            names = [item.split(".", 2)[2] for item in capability_ids_for_fact]
            duplicate_names = sorted(name for name, count in Counter(names).items() if count > 1)
            duplicate_names = [
                name
                for name in duplicate_names
                if not _is_aggregate_parameter_pair(
                    name,
                    capability_ids_for_fact,
                )
            ]
            if duplicate_names:
                issues.append(
                    _issue(
                        "error",
                        "semantic_fact_duplicate_name_classification",
                        ip=ip_id,
                        detail=(
                            f"{instance}:{kind}:{path} -> "
                            + ",".join(sorted(capability_ids_for_fact))
                        ),
                    )
                )
        classified = set(classifications)
        unclassified = {
            (item["instance"], item["kind"], item["path"]) for item in audit["unclassified"]
        }
        overlap = sorted(classified & unclassified)
        for instance, kind, path in overlap:
            issues.append(
                _issue(
                    "error",
                    "fact_classification_overlap",
                    ip=ip_id,
                    detail=f"{instance}:{kind}:{path}",
                )
            )
        counts["classified_facts"] = len(classified)
        reviewed = len(classified | unclassified)
        counts["semantic_fact_ratio"] = _ratio(len(classified), reviewed)

        non_identity_count = sum(
            category_counts[name]
            for name in (
                "features",
                "limits",
                "options",
                "parameters",
                "interrupts",
            )
        )
        identity_only = non_identity_count == 0
        if identity_only:
            if facts is None:
                review_state = "fact_ir_not_supplied"
                issue_code = "identity_only_profile"
                detail = "no feature, limit, option, or interrupt was proven"
            elif semantic_candidates:
                review_state = "explicit_candidates_unresolved"
                issue_code = "identity_only_with_explicit_candidates"
                detail = (
                    "no semantic capability was proven; explicit SVD candidate "
                    f"groups={len(semantic_candidates)}, "
                    f"facts={counts['semantic_candidate_facts']}"
                )
            else:
                review_state = "no_explicit_candidates"
                issue_code = "identity_only_without_explicit_candidates"
                detail = (
                    "no semantic capability or explicit generic SVD candidate "
                    f"was found; register surface={identity_surface}"
                )
            issues.append(
                _issue(
                    "warning",
                    issue_code,
                    ip=ip_id,
                    detail=detail,
                )
            )
        else:
            review_state = "not_identity_only"

        for conflict in semantic_candidate_conflicts:
            issues.append(
                _issue(
                    "warning",
                    "semantic_candidate_value_conflict",
                    ip=ip_id,
                    detail=(
                        f"{conflict['kind']}:{conflict['rule']}:"
                        f"{conflict['path_pattern']} access={conflict['access']} "
                        f"has {len(conflict['value_sets'])} value sets"
                    ),
                )
            )

        for conflict in parameter_domain_conflicts:
            issues.append(
                _issue(
                    "warning",
                    "component_parameter_domain_conflict",
                    ip=ip_id,
                    capability=conflict["capability"],
                    detail=(
                        "member-scoped component parameter has "
                        f"{len(conflict['value_sets'])} explicit value domains"
                    ),
                )
            )

        per_ip[ip_id] = {
            **counts,
            "capabilities": category_counts,
            "capability_ids": sorted(capability_ids),
            "identity_only": identity_only,
            "identity_only_review": review_state,
            "identity_only_surface": (identity_surface if identity_only else "not_applicable"),
            "audit_reason_counts": audit_reason_counts,
            "semantic_candidate_group_counts": candidate_group_counts,
            "semantic_candidate_fact_counts": candidate_fact_counts,
            "semantic_candidate_groups": semantic_candidates,
            "semantic_candidate_value_conflicts": semantic_candidate_conflicts,
            "parameter_domain_value_conflicts": parameter_domain_conflicts,
        }
        for key in totals:
            if key != "semantic_fact_ratio":
                totals[key] += counts[key]

    total_reviewed = totals["classified_facts"] + totals["unclassified_facts"]
    totals["semantic_fact_ratio"] = _ratio(totals["classified_facts"], total_reviewed)

    required = []
    for capability_id in sorted(set(required_capabilities)):
        result = _required_result(artifacts, capability_id)
        required.append(result)
        if not result["present"]:
            issues.append(
                _issue(
                    "error",
                    "required_capability_missing",
                    capability=capability_id,
                    detail=result["reason"],
                )
            )

    issues.sort(
        key=lambda item: (
            0 if item["severity"] == "error" else 1,
            item["code"],
            item.get("ip", ""),
            item.get("capability", ""),
            item["detail"],
        )
    )
    error_count = sum(item["severity"] == "error" for item in issues)
    warning_count = sum(item["severity"] == "warning" for item in issues)
    return {
        "schema": QUALITY_SCHEMA,
        "chip": chip_id,
        "source": source,
        "status": "pass" if error_count == 0 else "fail",
        "summary": {
            "profiles": len(profile_ids),
            **totals,
            "errors": error_count,
            "warnings": warning_count,
        },
        "required_capabilities": required,
        "per_ip": per_ip,
        "issues": issues,
    }


def _validated_fact_groups(
    facts: SvdFactIR | None,
    profile_ids: tuple[str, ...],
    source: Mapping[str, Any],
) -> dict[str, Any]:
    if facts is None:
        return {}
    if facts.source_sha256 != source.get("sha256"):
        raise ValueError("Fact IR and semantic artifacts use different SVD hashes")
    groups = {group.ip_id: group for group in facts.groups}
    if tuple(sorted(groups)) != profile_ids:
        raise ValueError("Fact IR and semantic artifacts use different IP sets")
    return groups


# Classify unresolved register access without inferring semantics.
def _identity_only_surface(group: IpGroup | None) -> str:

    if group is None:
        return "fact_ir_not_supplied"
    read_only = 0
    writable = 0
    for instance in group.instances:
        for register in instance.peripheral.registers:
            for field in register.fields:
                if field.access in {"read", "read-only"}:
                    read_only += 1
                else:
                    writable += 1
    if read_only and writable:
        return "mixed"
    if writable:
        return "writable"
    if read_only:
        return "read_only"
    return "empty"


def _field_details(
    group: IpGroup | None,
) -> dict[tuple[str, str], tuple[str, int]]:
    if group is None:
        return {}
    result: dict[tuple[str, str], tuple[str, int]] = {}
    for instance in group.instances:
        peripheral = instance.peripheral
        for register in peripheral.registers:
            register_path = f"{peripheral.svd_name}.{register.path}"
            for field in register.fields:
                mask = (1 << field.bit_width) - 1
                selected = (register.reset_value >> field.bit_offset) & mask
                result[(instance.instance_id, f"{register_path}.{field.name}")] = (
                    field.access,
                    selected,
                )
    return result


def _configurable_value_issues(
    capability_id: str,
    evidence: Iterable[Mapping[str, str]],
    field_details: Mapping[tuple[str, str], tuple[str, int]],
    *,
    ip_id: str,
) -> list[dict[str, str]]:
    issues = []
    for item in evidence:
        if item["kind"] != "field":
            continue
        detail = field_details.get((item["instance"], item["path"]))
        if detail is None or detail[0] in CONFIGURABLE_OPTION_ACCESS:
            continue
        access = detail[0]
        issues.append(
            _issue(
                "error",
                "non_configurable_value_capability",
                ip=ip_id,
                capability=capability_id,
                detail=(
                    f"{item['instance']}:{item['path']} access={access} "
                    "cannot prove a configurable value domain"
                ),
            )
        )
    return issues


def _feature_evidence_issues(
    capability_id: str,
    evidence: Iterable[Mapping[str, str]],
    field_details: Mapping[tuple[str, str], tuple[str, int]],
    *,
    ip_id: str,
) -> list[dict[str, str]]:
    issues = []
    for item in evidence:
        if item["kind"] != "field":
            continue
        detail = field_details.get((item["instance"], item["path"]))
        if detail is None:
            continue
        access, selected = detail
        if access not in {"read", "read-only"} or selected == 1:
            continue
        issues.append(
            _issue(
                "error",
                "disabled_readonly_feature_evidence",
                ip=ip_id,
                capability=capability_id,
                detail=(
                    f"{item['instance']}:{item['path']} access={access} "
                    f"selected={selected} cannot prove feature presence"
                ),
            )
        )
    return issues


def _parameter_evidence_issues(
    capability_id: str,
    evidence: Iterable[Mapping[str, str]],
    field_details: Mapping[tuple[str, str], tuple[str, int]],
    *,
    ip_id: str,
) -> list[dict[str, str]]:
    issues = []
    for item in evidence:
        detail = field_details.get((item["instance"], item["path"]))
        if (
            item["kind"] == "register"
            and item.get("member")
            and item.get("rule") == "mode_label_width"
        ):
            continue
        if (
            item["kind"] == "field"
            and item.get("member")
            and item.get("rule") == "readonly_component_parameter"
            and detail is not None
            and detail[0] in {"read", "read-only"}
        ):
            continue
        issues.append(
            _issue(
                "error",
                "invalid_component_parameter_evidence",
                ip=ip_id,
                capability=capability_id,
                detail=(
                    f"{item.get('instance')}:{item.get('path')} must be a "
                    "member-scoped read-only component parameter field"
                ),
            )
        )
    return issues


def _semantic_candidates(
    group: IpGroup | None,
    unclassified: Iterable[Mapping[str, str]],
) -> list[dict[str, Any]]:
    if group is None:
        return []
    audit_reasons = {
        (item["instance"], item["kind"], item["path"]): item["reason"] for item in unclassified
    }
    candidates: list[dict[str, Any]] = []
    for instance in group.instances:
        peripheral = instance.peripheral
        for register in peripheral.registers:
            register_path = f"{peripheral.svd_name}.{register.path}"
            for field in register.fields:
                path = f"{register_path}.{field.name}"
                key = (instance.instance_id, "field", path)
                reason = audit_reasons.get(key)
                if reason is None:
                    continue
                for marker in explicit_field_markers(field):
                    item: dict[str, Any] = {
                        "instance": instance.instance_id,
                        "kind": marker.kind,
                        "access": field.access,
                        "path": path,
                        "path_pattern": _candidate_path_pattern(
                            register.path,
                            field.name,
                        ),
                        "source_name": field.name,
                        "reason": reason,
                        "rule": marker.rule,
                    }
                    if marker.values:
                        item["values"] = list(marker.values)
                    candidates.append(item)
        for interrupt in peripheral.interrupts:
            path = f"{peripheral.svd_name}.interrupt.{interrupt.name}"
            key = (instance.instance_id, "interrupt", path)
            reason = audit_reasons.get(key)
            if reason is not None:
                candidates.append(
                    {
                        "instance": instance.instance_id,
                        "kind": "interrupt",
                        "access": "not-applicable",
                        "path": path,
                        "path_pattern": _candidate_path_pattern(
                            "interrupt",
                            interrupt.name,
                        ),
                        "source_name": interrupt.name,
                        "reason": reason,
                        "rule": "declared_interrupt",
                    }
                )
    return _group_candidates(candidates)


def _candidate_path_pattern(register_path: str, source_name: str) -> str:
    value = f"{register_path}.{source_name}".lower()
    return _NUMERIC_TOKEN.sub("#", value)


def _group_candidates(candidates: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in candidates:
        values = tuple(item.get("values", ()))
        key = (
            item["kind"],
            item["rule"],
            item["reason"],
            item["access"],
            item["path_pattern"],
            values,
        )
        group = grouped.setdefault(
            key,
            {
                "kind": item["kind"],
                "rule": item["rule"],
                "reason": item["reason"],
                "access": item["access"],
                "path_pattern": item["path_pattern"],
                "occurrence_count": 0,
                "instances": set(),
                "source_names": set(),
                "paths": [],
                "values": values,
            },
        )
        group["occurrence_count"] += 1
        group["instances"].add(item["instance"])
        group["source_names"].add(item["source_name"])
        group["paths"].append(item["path"])

    result: list[dict[str, Any]] = []
    for group in grouped.values():
        value = {
            "kind": group["kind"],
            "rule": group["rule"],
            "reason": group["reason"],
            "access": group["access"],
            "path_pattern": group["path_pattern"],
            "occurrence_count": group["occurrence_count"],
            "instances": sorted(group["instances"]),
            "source_names": sorted(group["source_names"]),
            "example_paths": sorted(group["paths"])[:3],
        }
        if group["values"]:
            value["values"] = list(group["values"])
        result.append(value)
    return sorted(
        result,
        key=lambda item: (
            item["kind"],
            item["path_pattern"],
            item["rule"],
        ),
    )


# Return same-shape candidates whose explicit value sets disagree.
#
# Numeric channel and instance suffixes are intentionally removed from the
# candidate path pattern.  A disagreement under the resulting shape can be a
# real per-channel implementation difference or a source-metadata defect.  It
# therefore requires review and must never be silently merged or corrected.
def _semantic_candidate_value_conflicts(
    candidates: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:

    grouped: dict[tuple[str, str, str, str], list[Mapping[str, Any]]] = {}
    for candidate in candidates:
        if "values" not in candidate:
            continue
        key = (
            str(candidate["kind"]),
            str(candidate["rule"]),
            str(candidate["access"]),
            str(candidate["path_pattern"]),
        )
        grouped.setdefault(key, []).append(candidate)

    conflicts: list[dict[str, Any]] = []
    for (kind, rule, access, path_pattern), groups in grouped.items():
        value_sets = {tuple(group["values"]) for group in groups}
        if len(value_sets) <= 1:
            continue
        variants = []
        for group in sorted(groups, key=lambda item: tuple(item["values"])):
            variants.append(
                {
                    "values": list(group["values"]),
                    "occurrence_count": group["occurrence_count"],
                    "source_names": list(group["source_names"]),
                    "example_paths": list(group["example_paths"]),
                }
            )
        conflicts.append(
            {
                "kind": kind,
                "rule": rule,
                "access": access,
                "path_pattern": path_pattern,
                "value_sets": variants,
            }
        )
    return sorted(
        conflicts,
        key=lambda item: (
            item["kind"],
            item["path_pattern"],
            item["rule"],
            item["access"],
        ),
    )


# Keep full SVD enum-domain disagreements visible after classification.
#
# A generated parameter stores the reset-selected implementation value.  The
# source field can still carry an inconsistent explicit enum domain (for
# example, a typo in one channel).  Classification must not hide that source
# quality problem from review.
def _parameter_domain_conflicts(
    group: IpGroup | None,
    profile: Mapping[str, Any],
) -> list[dict[str, Any]]:

    if group is None:
        return []
    evidence_to_capability: dict[tuple[str, str], tuple[str, str]] = {}
    for capability_id, items in profile["evidence"].items():
        if ".parameter." not in capability_id:
            continue
        for item in items:
            member = item.get("member")
            if item.get("kind") == "field" and member:
                evidence_to_capability[(item["instance"], item["path"])] = (
                    capability_id,
                    member,
                )

    grouped: dict[str, dict[tuple[Any, ...], dict[str, Any]]] = {}
    for instance in group.instances:
        peripheral = instance.peripheral
        for register in peripheral.registers:
            register_path = f"{peripheral.svd_name}.{register.path}"
            for field in register.fields:
                path = f"{register_path}.{field.name}"
                classified = evidence_to_capability.get((instance.instance_id, path))
                if classified is None:
                    continue
                capability_id, member = classified
                marker = next(
                    (
                        item
                        for item in explicit_field_markers(field)
                        if item.kind == "option" and item.values
                    ),
                    None,
                )
                if marker is None:
                    continue
                variants = grouped.setdefault(capability_id, {})
                variant = variants.setdefault(
                    tuple(marker.values),
                    {
                        "values": list(marker.values),
                        "occurrence_count": 0,
                        "instances": set(),
                        "members": set(),
                        "example_paths": [],
                    },
                )
                variant["occurrence_count"] += 1
                variant["instances"].add(instance.instance_id)
                variant["members"].add(member)
                variant["example_paths"].append(path)

    conflicts: list[dict[str, Any]] = []
    for capability_id, variants in grouped.items():
        if len(variants) <= 1:
            continue
        value_sets = []
        for value in sorted(variants.values(), key=lambda item: repr(item["values"])):
            value_sets.append(
                {
                    "values": value["values"],
                    "occurrence_count": value["occurrence_count"],
                    "instances": sorted(value["instances"]),
                    "members": sorted(value["members"]),
                    "example_paths": sorted(value["example_paths"])[:3],
                }
            )
        conflicts.append({"capability": capability_id, "value_sets": value_sets})
    return sorted(conflicts, key=lambda item: item["capability"])


# Return whether equal names intentionally express one semantic axis.
def _is_expected_cross_kind_name(kinds: Iterable[str]) -> bool:

    value = set(kinds)
    return value in (
        {"feature", "parameter"},
        {"option", "parameter"},
    )


def _is_aggregate_parameter_pair(
    name: str,
    capability_ids: Iterable[str],
) -> bool:
    matching_kinds = {
        capability_id.split(".", 2)[1]
        for capability_id in capability_ids
        if capability_id.split(".", 2)[2] == name
    }
    return matching_kinds == {"feature", "parameter"}


def _empty_counts() -> dict[str, int | float]:
    return {
        "instances": 0,
        "capability_definitions": 0,
        "capability_values": 0,
        "evidence_entries": 0,
        "classified_facts": 0,
        "unclassified_facts": 0,
        "semantic_candidate_groups": 0,
        "semantic_candidate_facts": 0,
        "semantic_candidate_conflicts": 0,
        "parameter_domain_conflicts": 0,
        "semantic_fact_ratio": 0.0,
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 1.0


def _name_issues(capability_id: str, name: str) -> list[dict[str, str]]:
    issues = []
    short = sorted(set(opaque_short_tokens(name)))
    # One short qualifier inside an otherwise descriptive name does not create
    # a large review burden.  Warn only when abbreviations dominate the lookup
    # phrase or the whole name is opaque.
    if has_dominant_short_tokens(name):
        issues.append(
            _issue(
                "warning",
                "short_name_token",
                capability=capability_id,
                detail="opaque short token(s): " + ",".join(short),
            )
        )
    if name in _GENERIC_NAMES or name.startswith("value_"):
        issues.append(
            _issue(
                "warning",
                "generic_capability_name",
                capability=capability_id,
                detail="name is too generic for stable natural-language lookup",
            )
        )
    return issues


def _required_result(artifacts: SemanticArtifacts, capability_id: str) -> dict[str, Any]:
    if not _CAPABILITY_ID.fullmatch(capability_id):
        return {
            "capability": capability_id,
            "present": False,
            "evidence_count": 0,
            "reason": "invalid capability ID",
        }
    ip_id, kind, name = capability_id.split(".", 2)
    profile = artifacts.profiles.get(ip_id)
    if profile is None:
        return {
            "capability": capability_id,
            "present": False,
            "evidence_count": 0,
            "reason": "IP profile is missing",
        }
    section = _SECTIONS[kind]
    present = name in profile["capabilities"][section]
    evidence_count = len(profile["evidence"].get(capability_id, ()))
    if not present:
        reason = "capability is missing"
    elif evidence_count == 0:
        reason = "capability has no evidence"
        present = False
    else:
        reason = ""
    return {
        "capability": capability_id,
        "present": present,
        "evidence_count": evidence_count,
        "reason": reason,
    }


def _issue(
    severity: str,
    code: str,
    *,
    detail: str,
    ip: str | None = None,
    capability: str | None = None,
) -> dict[str, str]:
    item = {"severity": severity, "code": code}
    if ip is not None:
        item["ip"] = ip
    if capability is not None:
        item["capability"] = capability
    item["detail"] = detail
    return item
