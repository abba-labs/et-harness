#!/usr/bin/env python3
# 确定性任务上下文编译与核对。
# 职责：从模块画像和Owner生成固定读写范围，并校验来源与任务基线。
# 边界：不批准硬件动作、不改源码、不自动选择任务或芯片。
# 依赖：Git、YAML、项目规则目录与文件Hash。

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from itertools import chain
from pathlib import Path, PurePosixPath
from typing import Any, TypeVar

import yaml

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_MAP = ROOT / "project-governance" / "system-map.yaml"
DEFAULT_OUTPUT = ROOT / "project-governance" / "runtime" / "current_task_context.json"
ACTIVE_TASK = ROOT.parent / "project-control" / "work" / "ACTIVE.md"
SUPPORTED_TOKENS = {"ip", "chip", "chip_upper"}
TASK_PARAMETER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
WORKTREE_EXCLUDES = ("artifacts/runs/**", "artifacts/reports/**", "artifacts/records/**")
HARDWARE_EXECUTION_LANES = {"fpga", "hil"}
KNOWLEDGE_REVIEW_CHANGE = "knowledge-review"
PIPELINE_RECORD_IP = "_PIPELINE"
PENDING_REVIEW_EXEMPT_MODULES = frozenset({"governance"})
PENDING_REVIEW_EXEMPT_DOCS = frozenset(
    {
        ("operator-pipeline", "docs"),
        ("pc-platform", "docs"),
        ("firmware-platform", "docs"),
    }
)
T = TypeVar("T")


# Return one stable SHA256 for a source file.
def _file_sha256(path: Path) -> str:

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


# Bind every security-relevant compiled field so runtime JSON cannot be widened in place.
def _context_integrity_fingerprint(context: Mapping[str, Any]) -> str:

    payload: dict[str, Any] = {
        "schema": context.get("schema"),
        "fingerprint": context.get("fingerprint"),
        "task": context.get("task"),
        "repository": context.get("repository"),
        "source_inputs": context.get("source_inputs"),
        "architecture": context.get("architecture"),
        "must_read": context.get("must_read"),
        "rule_owners": context.get("rule_owners"),
        "write_scope": context.get("write_scope"),
        "validation": context.get("validation"),
    }
    if "scope_baseline" in context:
        payload["scope_baseline"] = context.get("scope_baseline")
    if "worktree_fingerprint" in context:
        payload["worktree_fingerprint"] = context.get("worktree_fingerprint")
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


# Load one YAML mapping and reject empty or non-mapping roots.
def _load_yaml(path: Path) -> dict[str, Any]:

    payload = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: YAML root must be a mapping")
    return payload


# Resolve a repository-relative path without allowing absolute paths or traversal.
def _safe_repository_path(value: str) -> Path:

    candidate = PurePosixPath(value.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe repository-relative path: {value!r}")
    return ROOT.joinpath(*candidate.parts)


# Extract supported format tokens without accepting arbitrary Python formatting expressions.
def _path_tokens(value: str) -> set[str]:

    tokens: set[str] = set()
    cursor = 0
    while cursor < len(value):
        opening = value.find("{", cursor)
        if opening < 0:
            break
        closing = value.find("}", opening + 1)
        if closing < 0:
            raise ValueError(f"unclosed path token in {value!r}")
        token = value[opening + 1 : closing]
        if not token or not token.replace("_", "").isalnum():
            raise ValueError(f"invalid path token in {value!r}")
        tokens.add(token)
        cursor = closing + 1
    unknown = tokens - SUPPORTED_TOKENS
    if unknown:
        raise ValueError(f"unsupported path token(s) {sorted(unknown)} in {value!r}")
    return tokens


# Expand one templated path; optional entries with unavailable parameters are omitted.
def _expand_path(
    value: str,
    parameters: Mapping[str, str | None],
    *,
    required: bool,
) -> str | None:

    tokens = _path_tokens(value)
    missing = sorted(token for token in tokens if not parameters.get(token))
    if missing:
        if required:
            raise ValueError(f"path {value!r} requires task parameter(s) {missing}")
        return None
    expanded = value.format(**parameters).replace("\\", "/")
    _safe_repository_path(expanded)
    return expanded


# Expand one command template and reject unavailable or unsafe task parameters.
def _expand_command(value: str, parameters: Mapping[str, str | None]) -> str:

    tokens = _path_tokens(value)
    missing = sorted(token for token in tokens if not parameters.get(token))
    if missing:
        raise ValueError(f"command {value!r} requires task parameter(s) {missing}")
    return value.format(**parameters)


# Reject task parameters that could escape one logical chip or IP namespace.
def _validate_task_parameter(name: str, value: str | None) -> None:

    if value is not None and not TASK_PARAMETER_RE.fullmatch(value):
        raise ValueError(f"task parameter {name} must be one identifier, got {value!r}")


# 解析显式IP/change列表；不接受通配符、路径或重复IP声明，也不猜测依赖关系。
def _parse_ip_scopes(values: Sequence[str]) -> dict[str, list[str]]:

    scopes: dict[str, list[str]] = {}
    for value in values:
        ip, separator, changes = value.partition(":")
        if not separator or not changes or ip in scopes:
            raise ValueError(f"--ip-scope requires a unique IP:change[,change...] entry: {value!r}")
        scopes[ip] = changes.split(",")
    return scopes


# 校验逐IP最小范围，保留旧单IP入口；change合法性仍由对应模块画像判定。
def _validate_ip_scopes(
    ip: str | None, scopes: Mapping[str, Sequence[str]] | None
) -> dict[str, list[str]]:

    if scopes is None:
        return {}
    if not isinstance(scopes, Mapping) or not scopes:
        raise ValueError("ip_scopes must be a non-empty mapping")
    if ip is not None:
        raise ValueError("--ip and --ip-scope cannot be combined")
    normalized: dict[str, list[str]] = {}
    for name, changes in scopes.items():
        if not isinstance(name, str):
            raise ValueError("each scoped IP must be one identifier")
        _validate_task_parameter("ip", name)
        if isinstance(changes, str) or not isinstance(changes, (list, tuple)) or not changes:
            raise ValueError(f"IP {name} requires a non-empty change list")
        for change in changes:
            if not isinstance(change, str):
                raise ValueError(f"IP {name} change must be one identifier")
            _validate_task_parameter("change", change)
        if len(set(changes)) != len(changes):
            raise ValueError(f"IP {name} has duplicate changes")
        normalized[name] = list(changes)
    return normalized


# Require hardware execution tasks to load the one governed Operator path.
def _validate_hardware_execution_route(
    *,
    lanes: Sequence[str],
    modules: Sequence[str],
    changes: Sequence[str],
) -> None:

    hardware_lanes = set(lanes) & HARDWARE_EXECUTION_LANES
    documentation_only_result = set(changes) == {"test-result"}
    route_is_missing = "operator-pipeline" not in modules or "pipeline" not in changes
    if hardware_lanes and not documentation_only_result and route_is_missing:
        raise ValueError(
            "FPGA/HIL hardware tasks require module 'operator-pipeline' and "
            "change 'pipeline' so the governed R500 execution path is routed"
        )


# Keep knowledge-review as a unique clean-tree remedy; never widen it via hardware lanes.
def _validate_knowledge_review_route(
    *,
    lanes: Sequence[str],
    changes: Sequence[str],
    ip: str | None,
) -> None:

    if KNOWLEDGE_REVIEW_CHANGE not in changes:
        return
    if set(changes) != {KNOWLEDGE_REVIEW_CHANGE}:
        raise ValueError(
            "knowledge-review must be the only change kind; "
            "do not mix it with pipeline or other changes"
        )
    if set(lanes) & HARDWARE_EXECUTION_LANES:
        raise ValueError(
            "knowledge-review cannot use FPGA/HIL lanes; omit --lane or use docs/tooling only"
        )
    if ip is not None and ip != ip.upper():
        raise ValueError(f"knowledge-review --ip must be the on-disk uppercase IP name, got {ip!r}")


# Return branch, revision and dirty state without mutating the repository.
def _git_state() -> dict[str, Any]:

    def run(*arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    try:
        branch = run("branch", "--show-current")
        head = run("rev-parse", "HEAD")
        dirty = bool(run("status", "--porcelain"))
    except (OSError, subprocess.CalledProcessError):
        return {"available": False, "branch": None, "head": None, "dirty": None}
    return {"available": True, "branch": branch, "head": head, "dirty": dirty}


# Compare only immutable repository identity; dirty state is expected to change during a task.
def _repository_identity_matches(current: object, rebuilt: object) -> bool:

    if not isinstance(current, Mapping) or not isinstance(rebuilt, Mapping):
        return False
    return all(
        current.get(field) == rebuilt.get(field) for field in ("available", "branch", "head")
    )


# Capture only source-like Git changes; runtime evidence is outside task source scope.
def _git_worktree_snapshot() -> dict[str, str]:

    def paths_from(*arguments: str) -> set[str]:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "-c", "core.quotepath=false", *arguments],
            check=True,
            capture_output=True,
        )
        return {
            item.decode("utf-8", errors="surrogateescape").replace("\\", "/")
            for item in completed.stdout.split(b"\0")
            if item
        }

    try:
        exclusions = tuple(f":(exclude){value}" for value in WORKTREE_EXCLUDES)
        changed = paths_from("diff", "--name-only", "-z", "HEAD", "--", ".", *exclusions)
        changed.update(
            paths_from(
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                ".",
                *exclusions,
            )
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"cannot capture Git worktree baseline: {exc}") from exc

    snapshot: dict[str, str] = {}
    for relative in sorted(changed):
        path = _safe_repository_path(relative)
        snapshot[relative] = _file_sha256(path) if path.is_file() else "<deleted>"
    return snapshot


# Return paths whose content or Git presence changed after Task Context compilation.
def _changed_paths_since(
    baseline: Mapping[str, str],
    current: Mapping[str, str],
) -> list[str]:

    return sorted(
        path for path in set(baseline) | set(current) if baseline.get(path) != current.get(path)
    )


# Bind the captured file hashes to the Context, not only the authorization fields.
def _worktree_fingerprint(snapshot: Mapping[str, str]) -> str:

    return hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()


# Translate one path segment while keeping `*` and `?` inside that segment.
def _scope_segment_regex(segment: str) -> str:

    pieces: list[str] = []
    for character in segment:
        if character == "*":
            pieces.append("[^/]*")
        elif character == "?":
            pieces.append("[^/]")
        else:
            pieces.append(re.escape(character))
    return "".join(pieces)


# Compile the compact scope syntax: `*` is one segment and `**` is recursive.
def _scope_regex(scope: str) -> re.Pattern[str]:

    segments = scope.replace("\\", "/").split("/")
    pieces = ["^"]
    for index, segment in enumerate(segments):
        if segment == "**":
            if index == len(segments) - 1:
                pieces.append(".*" if index == 0 else "(?:/.*)?")
            else:
                pieces.append("(?:[^/]+/)*" if index == 0 else "/(?:[^/]+/)*")
            continue
        if index > 0 and segments[index - 1] != "**":
            pieces.append("/")
        pieces.append(_scope_segment_regex(segment))
    pieces.append("$")
    return re.compile("".join(pieces))


# Match one repository path against the compact scope syntax used by module profiles.
def _matches_scope(path: str, scope: str) -> bool:

    normalized_path = path.replace("\\", "/")
    normalized_scope = scope.replace("\\", "/")
    return _scope_regex(normalized_scope).fullmatch(normalized_path) is not None


# Report protected or out-of-scope changes using protected-scope precedence.
def _scope_violations(context: Mapping[str, Any], changed_paths: Sequence[str]) -> list[str]:

    write_scope = context.get("write_scope")
    if not isinstance(write_scope, dict):
        return ["Task Context write_scope must be a mapping"]
    allowed = write_scope.get("allowed")
    if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
        return ["Task Context write_scope.allowed must be a string list"]
    protected = write_scope.get("protected")
    if not isinstance(protected, list) or not all(isinstance(item, str) for item in protected):
        return ["Task Context write_scope.protected must be a string list"]

    errors: list[str] = []
    for path in changed_paths:
        if any(_matches_scope(path, scope) for scope in protected):
            errors.append(f"path is protected by task scope: {path}")
        elif not any(_matches_scope(path, scope) for scope in allowed):
            errors.append(f"path outside allowed task scope: {path}")
    return errors


# Load all active rule Owners by stable ID.
def _active_rule_owners(catalog: Mapping[str, Any]) -> dict[str, dict[str, Any]]:

    owners = catalog.get("owners")
    if not isinstance(owners, list):
        raise ValueError("rule Catalog owners must be a list")
    active: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(owners):
        if not isinstance(entry, dict):
            raise ValueError(f"rule Owner #{index} must be a mapping")
        if entry.get("lifecycle") != "active":
            continue
        owner_id = entry.get("id")
        if not isinstance(owner_id, str) or not owner_id:
            raise ValueError(f"active rule Owner #{index} has no stable id")
        if owner_id in active:
            raise ValueError(f"duplicate active rule Owner: {owner_id}")
        active[owner_id] = entry
    return active


# Validate one read entry's compact schema and safe path template.
def _validate_read_entry(entry: object, label: str) -> list[str]:

    if not isinstance(entry, dict):
        return [f"{label}: read entry must be a mapping"]
    errors: list[str] = []
    path = entry.get("path")
    reason = entry.get("reason")
    required = entry.get("required")
    if not isinstance(path, str) or not path:
        errors.append(f"{label}: read path must be a non-empty string")
    else:
        try:
            _path_tokens(path)
            static = path.replace("{ip}", "placeholder").replace("{chip}", "placeholder")
            _safe_repository_path(static)
        except ValueError as exc:
            errors.append(f"{label}: {exc}")
    if not isinstance(reason, str) or not reason:
        errors.append(f"{label}: read reason must be a non-empty string")
    if not isinstance(required, bool):
        errors.append(f"{label}: read required must be boolean")
    return errors


# Validate a list-valued string field.
def _validate_string_list(value: object, label: str) -> list[str]:

    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        return [f"{label} must be a string list"]
    return []


# Validate one module section shared by always and change-kind blocks.
def _validate_module_section(
    section: object,
    *,
    label: str,
    owner_ids: set[str],
) -> list[str]:

    if not isinstance(section, dict):
        return [f"{label} must be a mapping"]
    errors: list[str] = []
    allowed = {
        "read",
        "rules",
        "write_scopes",
        "protected_scopes",
        "validation",
        "required_parameters",
    }
    unknown = sorted(set(section) - allowed)
    if unknown:
        errors.append(f"{label}: unknown fields {unknown}")
    reads = section.get("read", [])
    if not isinstance(reads, list):
        errors.append(f"{label}.read must be a list")
    else:
        for index, entry in enumerate(reads):
            errors.extend(_validate_read_entry(entry, f"{label}.read[{index}]"))
    for field in ("rules", "write_scopes", "protected_scopes", "validation", "required_parameters"):
        value = section.get(field, [])
        errors.extend(_validate_string_list(value, f"{label}.{field}"))
        if field in {"write_scopes", "protected_scopes"} and isinstance(value, list):
            for item in value:
                if not isinstance(item, str):
                    continue
                try:
                    _path_tokens(item)
                    static = item.replace("{ip}", "placeholder").replace("{chip}", "placeholder")
                    _safe_repository_path(static)
                except ValueError as exc:
                    errors.append(f"{label}.{field}: {exc}")
    rules = section.get("rules", [])
    if isinstance(rules, list):
        unknown_rules = sorted(
            rule for rule in rules if isinstance(rule, str) and rule not in owner_ids
        )
        if unknown_rules:
            errors.append(f"{label}: unknown active rule Owner(s) {unknown_rules}")
    parameters = section.get("required_parameters", [])
    if isinstance(parameters, list):
        unknown_parameters = sorted(
            value
            for value in parameters
            if isinstance(value, str) and value not in SUPPORTED_TOKENS
        )
        if unknown_parameters:
            errors.append(f"{label}: unsupported required parameter(s) {unknown_parameters}")
    return errors


# Validate one module profile against the stable lightweight schema.
def _validate_module_profile(
    profile: Mapping[str, Any],
    *,
    expected_id: str,
    owner_ids: set[str],
) -> list[str]:

    errors: list[str] = []
    if profile.get("schema") != "et.module-profile.v1":
        errors.append(f"{expected_id}: schema must be et.module-profile.v1")
    if profile.get("id") != expected_id:
        errors.append(f"{expected_id}: profile id does not match system map")
    if not isinstance(profile.get("summary"), str) or not profile.get("summary"):
        errors.append(f"{expected_id}: summary must be a non-empty string")
    errors.extend(
        _validate_string_list(
            profile.get("architecture_chain"), f"{expected_id}.architecture_chain"
        )
    )
    parameters = profile.get("parameters")
    if not isinstance(parameters, dict):
        errors.append(f"{expected_id}.parameters must be a mapping")
    else:
        for field in ("required", "optional"):
            errors.extend(
                _validate_string_list(parameters.get(field), f"{expected_id}.parameters.{field}")
            )
        declared = set(parameters.get("required", [])) | set(parameters.get("optional", []))
        unknown = sorted(value for value in declared if value not in SUPPORTED_TOKENS)
        if unknown:
            errors.append(f"{expected_id}: unsupported parameter(s) {unknown}")
    errors.extend(
        _validate_module_section(
            profile.get("always"), label=f"{expected_id}.always", owner_ids=owner_ids
        )
    )
    changes = profile.get("changes")
    if not isinstance(changes, dict) or not changes:
        errors.append(f"{expected_id}.changes must be a non-empty mapping")
    else:
        for change, section in changes.items():
            if not isinstance(change, str) or not change:
                errors.append(f"{expected_id}: change kind must be a non-empty string")
                continue
            errors.extend(
                _validate_module_section(
                    section,
                    label=f"{expected_id}.changes.{change}",
                    owner_ids=owner_ids,
                )
            )
            if isinstance(section, dict):
                if not section.get("rules"):
                    errors.append(f"{expected_id}.changes.{change}.rules must not be empty")
                if not section.get("write_scopes"):
                    errors.append(f"{expected_id}.changes.{change}.write_scopes must not be empty")
                if not section.get("validation"):
                    errors.append(f"{expected_id}.changes.{change}.validation must not be empty")
    return errors


# Validate the system map's top-level path fields.
def _validate_system_map_paths(system_map: Mapping[str, Any]) -> list[str]:

    errors: list[str] = []
    constitution = system_map.get("constitution")
    if not isinstance(constitution, str) or not _safe_repository_path(constitution).is_file():
        errors.append("system map constitution must reference an existing file")
    runtime_context = system_map.get("runtime_context")
    if not isinstance(runtime_context, str):
        errors.append("system map runtime_context must be a repository-relative path")
    else:
        try:
            _safe_repository_path(runtime_context)
        except ValueError as exc:
            errors.append(str(exc))
    lanes = system_map.get("lanes")
    errors.extend(_validate_string_list(lanes, "system map lanes"))
    if isinstance(lanes, list):
        invalid = sorted(
            lane
            for lane in lanes
            if isinstance(lane, str) and not TASK_PARAMETER_RE.fullmatch(lane)
        )
        if invalid:
            errors.append(f"system map lanes contain invalid identifiers: {invalid}")
        if len(set(lanes)) != len(lanes):
            errors.append("system map lanes must be unique")
    return errors


# Validate every module registration, alias and profile.
def _validate_system_map_modules(
    modules: object,
    *,
    owner_ids: set[str],
) -> list[str]:

    if not isinstance(modules, list) or not modules:
        return ["system map modules must be a non-empty list"]
    errors: list[str] = []

    seen_ids: set[str] = set()
    seen_aliases: dict[str, str] = {}
    for index, entry in enumerate(modules):
        if not isinstance(entry, dict):
            errors.append(f"system map module #{index} must be a mapping")
            continue
        module_id = entry.get("id")
        profile_value = entry.get("profile")
        aliases = entry.get("aliases")
        if not isinstance(module_id, str) or not module_id:
            errors.append(f"system map module #{index} has no stable id")
            continue
        if module_id in seen_ids:
            errors.append(f"duplicate module id: {module_id}")
        seen_ids.add(module_id)
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) and alias for alias in aliases
        ):
            errors.append(f"{module_id}: aliases must be a string list")
        else:
            for alias in aliases:
                prior = seen_aliases.get(alias)
                if prior is not None and prior != module_id:
                    errors.append(f"alias {alias!r} belongs to both {prior} and {module_id}")
                seen_aliases[alias] = module_id
        if not isinstance(profile_value, str):
            errors.append(f"{module_id}: profile must be a path")
            continue
        try:
            profile_path = _safe_repository_path(profile_value)
            profile = _load_yaml(profile_path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{module_id}: invalid profile: {exc}")
            continue
        errors.extend(_validate_module_profile(profile, expected_id=module_id, owner_ids=owner_ids))
    for alias, owner in seen_aliases.items():
        if alias in seen_ids and alias != owner:
            errors.append(f"alias {alias!r} conflicts with module id {alias!r}")
    return errors


# Resolve canonical module IDs and their declared human-friendly aliases.
def _module_indexes(
    system_map: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, str]]:

    module_index = {entry["id"]: entry for entry in system_map["modules"]}
    alias_index = {
        alias: entry["id"] for entry in system_map["modules"] for alias in entry.get("aliases", [])
    }
    return module_index, alias_index


# Validate the project map, all profiles and all referenced active rule Owners.
def validate_navigation() -> list[str]:

    errors: list[str] = []
    try:
        system_map = _load_yaml(SYSTEM_MAP)
        if system_map.get("schema") != "et.project-system-map.v1":
            errors.append("system map schema must be et.project-system-map.v1")
        catalog_value = system_map.get("rule_catalog")
        if not isinstance(catalog_value, str):
            return [*errors, "system map rule_catalog must be a path"]
        catalog_path = _safe_repository_path(catalog_value)
        owners = _active_rule_owners(_load_yaml(catalog_path))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"navigation source is invalid: {exc}"]
    errors.extend(_validate_system_map_paths(system_map))
    errors.extend(_validate_system_map_modules(system_map.get("modules"), owner_ids=set(owners)))
    return sorted(set(errors))


# Append unique scalar values while preserving their declared order.
def _extend_unique(target: list[T], values: Iterable[T]) -> None:

    for value in values:
        if value not in target:
            target.append(value)


# Add one source file to the Task Context input-fingerprint set.
def _source_input(target: list[dict[str, str]], path: Path) -> None:

    relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
    entry = {"path": relative, "sha256": _file_sha256(path)}
    if entry not in target:
        target.append(entry)


# Return original navigation inputs whose content changed during the authorized task.
def _changed_source_inputs(context: Mapping[str, Any]) -> list[str]:

    entries = context.get("source_inputs")
    if not isinstance(entries, list):
        return ["<invalid-source-inputs>"]
    changed: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            return ["<invalid-source-input-entry>"]
        value = entry.get("path")
        expected = entry.get("sha256")
        if not isinstance(value, str) or not isinstance(expected, str):
            return ["<invalid-source-input-entry>"]
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = _safe_repository_path(value)
        actual = _file_sha256(candidate) if candidate.is_file() else "<missing>"
        if actual != expected:
            changed.append(value.replace("\\", "/"))
    return changed


# Check whether changed navigation inputs were already writable in the original Task Context.
def _changed_inputs_are_authorized(
    context: Mapping[str, Any],
    changed_inputs: Sequence[str],
) -> bool:

    write_scope = context.get("write_scope")
    if not isinstance(write_scope, dict):
        return False
    allowed = write_scope.get("allowed")
    protected = write_scope.get("protected")
    if (
        not isinstance(allowed, list)
        or not all(isinstance(item, str) for item in allowed)
        or not isinstance(protected, list)
        or not all(isinstance(item, str) for item in protected)
    ):
        return False
    for value in changed_inputs:
        candidate = Path(value)
        if candidate.is_absolute():
            try:
                relative = candidate.resolve().relative_to(ROOT).as_posix()
            except ValueError:
                return False
        else:
            relative = value
        if any(_matches_scope(relative, scope) for scope in protected):
            return False
        if not any(_matches_scope(relative, scope) for scope in allowed):
            return False
    return bool(changed_inputs)


# Convert one read declaration into one concrete, existence-checked navigation record.
def _materialize_read(
    entry: Mapping[str, Any],
    parameters: Mapping[str, str | None],
) -> dict[str, Any] | None:

    required = bool(entry["required"])
    value = _expand_path(str(entry["path"]), parameters, required=required)
    if value is None:
        return None
    path = _safe_repository_path(value)
    return {
        "path": value,
        "reason": str(entry["reason"]),
        "required": required,
        "exists": path.exists(),
    }


# Select the applicable sections of one module and enforce their explicit parameters.
def _select_module_sections(
    profile: Mapping[str, Any],
    *,
    module_id: str,
    changes: Sequence[str],
    parameters: Mapping[str, str | None],
) -> tuple[list[Mapping[str, Any]], set[str]]:

    required_parameters = profile["parameters"]["required"]
    missing = sorted(value for value in required_parameters if not parameters.get(value))
    if missing:
        raise ValueError(f"module {module_id} requires task parameter(s) {missing}")
    sections: list[Mapping[str, Any]] = [profile["always"]]
    matched: set[str] = set()
    for change in changes:
        section = profile["changes"].get(change)
        if section is None:
            continue
        matched.add(change)
        change_required = section.get("required_parameters", [])
        change_missing = sorted(value for value in change_required if not parameters.get(value))
        if change_missing:
            raise ValueError(
                f"module {module_id} change {change} requires task parameter(s) {change_missing}"
            )
        sections.append(section)
    return sections, matched


# Materialize one module's context fragment without merging global task state.
def _module_context_fragment(
    *,
    module_id: str,
    module_entry: Mapping[str, Any],
    changes: Sequence[str],
    parameters: Mapping[str, str | None],
) -> dict[str, Any]:

    profile_path = _safe_repository_path(str(module_entry["profile"]))
    profile = _load_yaml(profile_path)
    sections, matched = _select_module_sections(
        profile,
        module_id=module_id,
        changes=changes,
        parameters=parameters,
    )
    reads: list[dict[str, Any]] = []
    rules: list[str] = []
    write_scopes: list[str] = []
    protected_scopes: list[str] = []
    validations: list[str] = []
    for section in sections:
        for entry in section.get("read", []):
            record = _materialize_read(entry, parameters)
            if record is not None and not any(prior["path"] == record["path"] for prior in reads):
                reads.append(record)
        _extend_unique(rules, section.get("rules", []))
        _extend_unique(protected_scopes, section.get("protected_scopes", []))
        _extend_unique(write_scopes, section.get("write_scopes", []))
        _extend_unique(validations, section.get("validation", []))
    return {
        "profile_path": profile_path,
        "matched_changes": matched,
        "architecture": {
            "module": module_id,
            "summary": profile["summary"],
            "chain": profile["architecture_chain"],
        },
        "reads": reads,
        "rules": rules,
        "write_scopes": [
            value
            for item in write_scopes
            if (value := _expand_path(item, parameters, required=False)) is not None
        ],
        "protected_scopes": [
            value
            for item in protected_scopes
            if (value := _expand_path(item, parameters, required=False)) is not None
        ],
        "validation": [_expand_command(item, parameters) for item in validations],
    }


# 将各模块的请求拆成独立展开单元；仅IP模块消费逐IPchange，不交叉授权。
def _module_requests(
    modules: Sequence[str],
    module_index: Mapping[str, Any],
    changes: Sequence[str],
    parameters: Mapping[str, str | None],
    scoped_ips: Mapping[str, Sequence[str]],
) -> list[tuple[str, Sequence[str], Mapping[str, str | None]]]:

    if scoped_ips and "ip-package" not in modules:
        raise ValueError("--ip-scope requires module 'ip-package'")
    requests = []
    for module_id in dict.fromkeys(modules):
        if module_id == "ip-package" and scoped_ips:
            profile = _load_yaml(_safe_repository_path(str(module_index[module_id]["profile"])))
            if set(changes) & set(profile["changes"]):
                raise ValueError(
                    "with --ip-scope, IP changes must be declared per IP, not --change"
                )
            for scoped_ip, scoped_changes in scoped_ips.items():
                unknown = set(scoped_changes) - set(profile["changes"])
                if unknown:
                    raise ValueError(f"IP {scoped_ip} has unsupported changes: {sorted(unknown)}")
                requests.append((module_id, scoped_changes, {**parameters, "ip": scoped_ip}))
        else:
            requests.append((module_id, changes, parameters))
    return requests


# Build one Task Context without writing it, so compile and stale-check share exactly one path.
def build_task_context(
    *,
    task_id: str,
    intent: str,
    modules: Sequence[str],
    changes: Sequence[str],
    ip: str | None = None,
    chip: str | None = None,
    lanes: Sequence[str] = (),
    ip_scopes: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:

    if not task_id.strip() or not intent.strip():
        raise ValueError("task_id and intent must be non-empty")
    scoped_ips = _validate_ip_scopes(ip, ip_scopes)
    if not modules or not (changes or scoped_ips):
        raise ValueError("at least one module and one change kind are required")
    _validate_task_parameter("ip", ip)
    _validate_task_parameter("chip", chip)
    errors = validate_navigation()
    if errors:
        raise ValueError("navigation governance is invalid:\n- " + "\n- ".join(errors))
    system_map = _load_yaml(SYSTEM_MAP)
    declared_lanes = set(system_map["lanes"])
    unknown_lanes = sorted(set(lanes) - declared_lanes)
    if unknown_lanes:
        raise ValueError(f"unknown task lane(s): {unknown_lanes}")
    catalog_path = _safe_repository_path(str(system_map["rule_catalog"]))
    catalog = _load_yaml(catalog_path)
    owner_index = _active_rule_owners(catalog)
    module_index, alias_index = _module_indexes(system_map)
    canonical_modules = [
        value if value in module_index else alias_index.get(value, value) for value in modules
    ]
    unknown_modules = sorted(set(canonical_modules) - set(module_index))
    if unknown_modules:
        raise ValueError(f"unknown module(s): {unknown_modules}")
    all_changes = list(dict.fromkeys(chain(changes, *scoped_ips.values())))
    _validate_knowledge_review_route(lanes=lanes, changes=all_changes, ip=ip)
    _validate_hardware_execution_route(
        lanes=lanes,
        modules=canonical_modules,
        changes=all_changes,
    )
    parameters = {"ip": ip, "chip": chip, "chip_upper": chip.upper() if chip else None}
    must_read: list[dict[str, Any]] = []
    rule_ids: list[str] = []
    write_scopes: list[str] = []
    protected_scopes: list[str] = []
    validations: list[str] = []
    architecture: list[dict[str, Any]] = []
    source_inputs: list[dict[str, str]] = []
    matched_changes: set[str] = set()
    matched_changes_by_module: dict[str, list[str]] = {}

    _source_input(source_inputs, SYSTEM_MAP)
    _source_input(source_inputs, catalog_path)
    _source_input(source_inputs, _safe_repository_path(str(system_map["constitution"])))
    if ACTIVE_TASK.is_file():
        _source_input(source_inputs, ACTIVE_TASK)

    for module_id, requested_changes, scoped_parameters in _module_requests(
        canonical_modules, module_index, changes, parameters, scoped_ips
    ):
        fragment = _module_context_fragment(
            module_id=module_id,
            module_entry=module_index[module_id],
            changes=requested_changes,
            parameters=scoped_parameters,
        )
        _source_input(source_inputs, fragment["profile_path"])
        matched_changes.update(fragment["matched_changes"])
        module_matches = sorted(fragment["matched_changes"])
        if not module_matches:
            raise ValueError(
                f"module {module_id} does not support any requested change kind: "
                f"{list(dict.fromkeys(requested_changes))}"
            )
        _extend_unique(matched_changes_by_module.setdefault(module_id, []), module_matches)
        _extend_unique(architecture, [fragment["architecture"]])
        for record in fragment["reads"]:
            if not any(prior["path"] == record["path"] for prior in must_read):
                must_read.append(record)
        _extend_unique(rule_ids, fragment["rules"])
        _extend_unique(protected_scopes, fragment["protected_scopes"])
        _extend_unique(write_scopes, fragment["write_scopes"])
        _extend_unique(validations, fragment["validation"])

    unmatched_changes = sorted(set(all_changes) - matched_changes)
    if unmatched_changes:
        raise ValueError(
            f"change kind(s) are not supported by selected modules: {unmatched_changes}"
        )

    rule_owners: list[dict[str, Any]] = []
    for owner_id in rule_ids:
        owner = owner_index[owner_id]
        source = str(owner["source"])
        rule_owners.append(
            {
                "owner_id": owner_id,
                "rule_id": owner["rule_id"],
                "source": source,
                "heading": owner["heading"],
            }
        )
        source_path = _safe_repository_path(source)
        _source_input(source_inputs, source_path)
        if not any(entry["path"] == source for entry in must_read):
            must_read.append(
                {
                    "path": source,
                    "reason": f"活动规则Owner：{owner_id} / {owner['heading']}",
                    "required": True,
                    "exists": source_path.is_file(),
                }
            )

    missing_required = [
        entry["path"] for entry in must_read if entry["required"] and not entry["exists"]
    ]
    if missing_required:
        raise ValueError(f"required navigation source(s) do not exist: {missing_required}")

    source_inputs.sort(key=lambda item: item["path"])
    task = {
        "id": task_id,
        "intent": intent,
        "modules": list(dict.fromkeys(canonical_modules)),
        "changes": list(dict.fromkeys(changes)),
        "lanes": list(dict.fromkeys(lanes)),
        "ip": ip,
        "chip": chip,
        "matched_changes_by_module": matched_changes_by_module,
    }
    # 仅新入口增加此字段，旧单IP上下文的结构和指纹保持兼容。
    task.update({"ip_scopes": scoped_ips} if scoped_ips else {})
    git_state = _git_state()
    fingerprint_payload = {
        "task": task,
        "source_inputs": source_inputs,
        "git": {
            "available": git_state["available"],
            "branch": git_state["branch"],
            "head": git_state["head"],
        },
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    context = {
        "schema": "et.task-context.v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "fingerprint": fingerprint,
        "task": task,
        "repository": git_state,
        "source_inputs": source_inputs,
        "architecture": architecture,
        "must_read": must_read,
        "rule_owners": rule_owners,
        "write_scope": {
            "allowed": write_scopes,
            "protected": protected_scopes,
        },
        "validation": validations,
    }
    context["integrity_fingerprint"] = _context_integrity_fingerprint(context)
    return context


# Locate one CHIP/IP current workspace without scanning the records tree.
def _record_current_dir(chip: str, ip: str) -> Path:

    return ROOT / "artifacts" / "records" / chip.upper() / ip.upper() / "current"


# A missing receipt is not pending; damaged or unreadable receipts fail closed.
def _publication_pending(path: Path) -> bool:

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return False
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read knowledge review receipt: {path}: {exc}") from exc
    if not isinstance(payload, dict) or type(payload.get("pending_review")) is not bool:
        raise ValueError(f"invalid knowledge review receipt pending_review: {path}")
    return payload["pending_review"]


# Parse one Pipeline test_workspaces entry into an IP name; skip unusable shapes.
def _ip_from_test_workspace(chip: str, value: object) -> str | None:

    if not isinstance(value, str) or not value:
        return None
    parts = PurePosixPath(value.replace("\\", "/")).parts
    if (
        len(parts) != 5
        or parts[0] != "artifacts"
        or parts[1] != "records"
        or parts[2].upper() != chip.upper()
        or parts[4] != "current"
        or parts[3] in {"", PIPELINE_RECORD_IP}
    ):
        return None
    return parts[3].upper()


# Collect IPs listed by a chip Pipeline manifest; absent or invalid files yield none.
def _pipeline_workspace_ips(chip: str) -> list[str]:

    manifest_path = _record_current_dir(chip, PIPELINE_RECORD_IP) / "manifest.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    workspaces = payload.get("test_workspaces")
    if not isinstance(workspaces, list):
        return []
    ips: list[str] = []
    for item in workspaces:
        ip = _ip_from_test_workspace(chip, item)
        if ip is not None:
            ips.append(ip)
    return list(dict.fromkeys(ips))


# Collect CHIP/IP names already bound on this compiled task; never scan the tree.
def _task_target_ips(task: Mapping[str, Any]) -> list[str]:

    targets: list[str] = []
    ip = task.get("ip")
    if isinstance(ip, str) and ip:
        targets.append(ip.upper())
    scopes = task.get("ip_scopes")
    if isinstance(scopes, Mapping):
        for name in scopes:
            if isinstance(name, str) and name:
                targets.append(name.upper())
    return list(dict.fromkeys(targets))


# True when every selected module/change is on the pending-review exemption allowlist.
def _pending_gate_exempt(matched: Mapping[str, Any]) -> bool:

    if not matched:
        return False
    for module_id, changes in matched.items():
        if not isinstance(changes, list) or not changes:
            return False
        for change in changes:
            if module_id in PENDING_REVIEW_EXEMPT_MODULES:
                continue
            if (str(module_id), str(change)) in PENDING_REVIEW_EXEMPT_DOCS:
                continue
            return False
    return True


# Build the unique knowledge-review compile line Agents must use as the skip remedy.
def _knowledge_review_remedy(chip: str | None, ip: str | None) -> str:

    chip_token = chip or "<CHIP>"
    ip_token = ip or "<IP>"
    return (
        "python tools/governance/compile_task_context.py compile "
        '--task-id <id> --intent "<intent>" '
        "--module operator-pipeline --change knowledge-review "
        f"--chip {chip_token} --ip {ip_token} "
        "(no --lane fpga/hil, no extra --change pipeline)"
    )


# Fail closed when a named target still has pending_review and this is not the remedy change.
def _reject_pending_knowledge_review(context: Mapping[str, Any]) -> None:

    task = context.get("task")
    if not isinstance(task, Mapping):
        raise ValueError("compiled Task Context task must be a mapping")
    matched = task.get("matched_changes_by_module")
    if not isinstance(matched, Mapping):
        matched = {}
    selected_changes: set[str] = set()
    for changes in matched.values():
        if isinstance(changes, list):
            selected_changes.update(str(item) for item in changes)
    if selected_changes == {KNOWLEDGE_REVIEW_CHANGE}:
        return
    if _pending_gate_exempt(matched):
        return
    chip_value = task.get("chip")
    chip = chip_value.upper() if isinstance(chip_value, str) and chip_value else None
    target_ips = _task_target_ips(task)
    if chip is None and target_ips:
        raise ValueError(
            "pending-review compile gate requires --chip to locate "
            f"records for IP(s) {target_ips}; do not guess the chip and do not "
            "scan artifacts/records"
        )
    if chip is None:
        if HARDWARE_EXECUTION_LANES.intersection(task.get("lanes", [])):
            raise ValueError("hardware execution requires --chip for knowledge review checks")
        # 无IP/芯片的公共软件任务没有运行现场；不得猜芯片或扫描全部证据。
        return
    probe_ips = list(target_ips)
    if not probe_ips:
        probe_ips.append(PIPELINE_RECORD_IP)
        probe_ips.extend(_pipeline_workspace_ips(chip))
        probe_ips = list(dict.fromkeys(probe_ips))
    for ip in probe_ips:
        receipt = _record_current_dir(chip, ip) / "publication.json"
        if not _publication_pending(receipt):
            continue
        try:
            display = receipt.relative_to(ROOT).as_posix()
        except ValueError:
            display = receipt.as_posix()
        raise ValueError(
            f"knowledge review is pending for {chip}/{ip} at {display}; "
            "non-knowledge-review compile is closed until review. "
            f"Using the fixed-baseline rules in R002, compile the remedy change only: "
            f"{_knowledge_review_remedy(chip, ip)}"
        )


# Write one compiled Task Context atomically enough for a local single-agent workflow.
def compile_task_context(args: argparse.Namespace) -> Path:

    context = build_task_context(
        task_id=args.task_id,
        intent=args.intent,
        modules=args.module,
        changes=args.change,
        ip=args.ip,
        chip=args.chip,
        lanes=args.lane,
        ip_scopes=_parse_ip_scopes(args.ip_scope) if getattr(args, "ip_scope", None) else None,
    )
    preserve_existing = getattr(args, "preserve_existing_changes", False)
    if (
        context["repository"]["available"]
        and context["repository"]["dirty"]
        and not preserve_existing
    ):
        raise ValueError(
            "Git worktree must be clean before compiling Task Context; "
            "use --preserve-existing-changes only for a human-authorized new task boundary"
        )
    _reject_pending_knowledge_review(context)
    output = Path(args.output).resolve() if args.output else DEFAULT_OUTPUT
    baseline_path = output.with_suffix(output.suffix + ".baseline.json")
    if preserve_existing and (output.exists() or baseline_path.exists()):
        raise ValueError(
            "preserved baseline already exists; use a distinct task output, never rebase it"
        )
    if output.exists():
        previous = json.loads(output.read_text(encoding="utf-8-sig"))
        if not isinstance(previous, dict):
            raise ValueError("existing Context is invalid; preserve it for diagnosis")
        if previous.get("worktree_fingerprint") and previous.get("repository", {}).get("dirty"):
            raise ValueError(
                "preserved baseline already exists; it cannot be replaced in clean mode"
            )
    snapshot = _git_worktree_snapshot() if context["repository"]["available"] else {}
    if preserve_existing and not context["repository"]["available"]:
        raise ValueError("preserving existing changes requires a Git worktree")
    if context["repository"]["available"]:
        if not _repository_identity_matches(context["repository"], _git_state()):
            raise ValueError("repository identity changed during baseline capture")
        if snapshot != _git_worktree_snapshot():
            raise ValueError("worktree changed during baseline capture; stop concurrent edits")
    context["scope_baseline"] = baseline_path.name
    context["worktree_fingerprint"] = _worktree_fingerprint(snapshot)
    context["integrity_fingerprint"] = _context_integrity_fingerprint(context)
    baseline = {
        "schema": "et.task-scope-baseline.v1",
        "repository": context["repository"],
        "context_integrity_fingerprint": context["integrity_fingerprint"],
        "write_scope": context["write_scope"],
        "worktree": snapshot,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    baseline_temporary = baseline_path.with_suffix(baseline_path.suffix + ".tmp")
    temporary.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    baseline_temporary.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    baseline_temporary.replace(baseline_path)
    temporary.replace(output)
    return output


# Rebuild the current context from its task declaration and compare stable fingerprints.
def check_task_context(path: Path) -> list[str]:

    stale_error = "Task Context is stale; recompile it before continuing"
    try:
        current = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read Task Context: {exc}"]
    if not isinstance(current, dict) or current.get("schema") != "et.task-context.v1":
        return ["Task Context schema must be et.task-context.v1"]
    if current.get("integrity_fingerprint") != _context_integrity_fingerprint(current):
        return [stale_error]
    task = current.get("task")
    if not isinstance(task, dict):
        return ["Task Context task must be a mapping"]
    try:
        rebuilt = build_task_context(
            task_id=str(task["id"]),
            intent=str(task["intent"]),
            modules=list(task["modules"]),
            changes=list(task["changes"]),
            ip=task.get("ip"),
            chip=task.get("chip"),
            lanes=list(task.get("lanes", [])),
            ip_scopes=task.get("ip_scopes"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"cannot rebuild Task Context: {exc}"]
    if not _repository_identity_matches(current.get("repository"), rebuilt.get("repository")):
        return [stale_error]
    if rebuilt["fingerprint"] != current.get("fingerprint"):
        changed_inputs = _changed_source_inputs(current)
        if _changed_inputs_are_authorized(current, changed_inputs):
            return []
        return [stale_error]
    return []


def _baseline_fingerprint_errors(current: dict, baseline: dict, repository: dict) -> list[str]:
    expected = current.get("worktree_fingerprint")
    if expected is not None:
        if expected != _worktree_fingerprint(baseline):
            return ["Task Scope baseline file hashes do not match the fixed Context fingerprint"]
    elif repository.get("dirty"):
        return ["dirty baseline requires a fixed worktree fingerprint"]
    return []


# Compare post-compilation source changes with the Task Context's allowed write scope.
def check_task_scope(path: Path) -> tuple[list[str], list[str]]:

    stale_error = "Task Context is stale; recompile it before continuing"
    try:
        current = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"cannot read Task Context: {exc}"]
    if not isinstance(current, dict) or current.get("schema") != "et.task-context.v1":
        return [], ["Task Context schema must be et.task-context.v1"]
    if current.get("integrity_fingerprint") != _context_integrity_fingerprint(current):
        return [], [stale_error]
    repository = current.get("repository")
    baseline_name = current.get("scope_baseline")
    if (
        not isinstance(repository, dict)
        or not isinstance(baseline_name, str)
        or not baseline_name
        or Path(baseline_name).name != baseline_name
    ):
        return [], ["Task Context has no valid scope baseline reference; recompile it"]
    baseline_path = path.parent / baseline_name
    try:
        baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"cannot read Task Scope baseline: {exc}"]
    baseline_write_scope = None
    if isinstance(baseline_payload, dict):
        baseline_write_scope = baseline_payload.get("write_scope")
    if (
        not isinstance(baseline_payload, dict)
        or baseline_payload.get("schema") != "et.task-scope-baseline.v1"
        or baseline_payload.get("repository") != repository
        or baseline_payload.get("context_integrity_fingerprint")
        != current.get("integrity_fingerprint")
        or baseline_write_scope != current.get("write_scope")
    ):
        return [], ["Task Scope baseline authorization does not match the Task Context"]
    baseline = baseline_payload.get("worktree")
    if not isinstance(baseline, dict):
        return [], ["Task Scope baseline worktree must be a mapping"]
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in baseline.items()):
        return [], ["Task Scope baseline must map paths to fingerprints"]
    fingerprint_errors = _baseline_fingerprint_errors(current, baseline, repository)
    if fingerprint_errors:
        return [], fingerprint_errors

    git_state = _git_state()
    if not git_state["available"]:
        return [], ["cannot audit task scope outside a Git worktree"]
    if git_state["branch"] != repository.get("branch") or git_state["head"] != repository.get(
        "head"
    ):
        return [], ["repository branch or HEAD changed; compile a new Task Context"]
    try:
        changed_paths = _changed_paths_since(baseline, _git_worktree_snapshot())
    except ValueError as exc:
        return [], [str(exc)]
    return changed_paths, _scope_violations({"write_scope": baseline_write_scope}, changed_paths)


# Define the compact CLI used by both Agents and the software gate.
def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:

    parser = argparse.ArgumentParser(description="Compile deterministic task navigation context.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="validate system map, profiles and rule Owners")
    compile_parser = subparsers.add_parser("compile", help="compile one task context")
    compile_parser.add_argument("--task-id", required=True)
    compile_parser.add_argument("--intent", required=True)
    compile_parser.add_argument("--module", action="append", required=True)
    compile_parser.add_argument("--change", action="append", default=[])
    compile_parser.add_argument("--lane", action="append", default=[])
    compile_parser.add_argument("--ip")
    compile_parser.add_argument(
        "--ip-scope",
        action="append",
        default=[],
        metavar="IP:CHANGE[,CHANGE...]",
        help="explicit per-IP changes; repeat for each IP, mutually exclusive with --ip",
    )
    compile_parser.add_argument("--chip")
    compile_parser.add_argument("--output")
    compile_parser.add_argument(
        "--preserve-existing-changes",
        action="store_true",
        help="freeze existing changes for a human-authorized new task; never overwrite its baseline",
    )
    check_parser = subparsers.add_parser("check", help="check whether current context is stale")
    check_parser.add_argument("--context", default=str(DEFAULT_OUTPUT))
    scope_parser = subparsers.add_parser(
        "scope-check", help="check changes made after compilation against allowed write scopes"
    )
    scope_parser.add_argument("--context", default=str(DEFAULT_OUTPUT))
    return parser.parse_args(argv)


# 分派编译或只读核对命令；治理、身份或范围错误返回非零，不放宽任务授权。
def main(argv: Sequence[str] | None = None) -> int:

    args = _parse_args(argv)
    if args.command == "validate":
        errors = validate_navigation()
        for error in errors:
            print(error, file=sys.stderr)
        if errors:
            print(
                f"Task navigation validation failed: {len(errors)} violation(s).", file=sys.stderr
            )
            return 1
        print("Task navigation validation passed.")
        return 0
    if args.command == "compile":
        try:
            output = compile_task_context(args)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            print(f"Task Context compilation failed: {exc}", file=sys.stderr)
            return 1
        print(f"Task Context compiled: {output}")
        return 0
    if args.command == "scope-check":
        changed_paths, errors = check_task_scope(Path(args.context))
        for error in errors:
            print(error, file=sys.stderr)
        if errors:
            return 1
        print(f"Task scope check passed: {len(changed_paths)} changed path(s).")
        return 0
    errors = check_task_context(Path(args.context))
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print("Task Context is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
