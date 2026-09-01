# Strict, chip-independent test capability requirement manifests.

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "et-test-capability-requirements/v1"
_ROOT_KEYS = {"schema", "suite", "required_capabilities"}
_SUITE_ID = re.compile(r"^[a-z][a-z0-9_.-]*$")
_CAPABILITY_ID = re.compile(
    r"^[a-z][a-z0-9_]*\."
    r"(?:feature|limit|option|parameter|interrupt|identity)\."
    r"[a-z][a-z0-9_.]*$"
)


# One test suite's immutable semantic capability dependencies.
@dataclass(frozen=True)
class CapabilityRequirements:
    suite: str
    required_capabilities: tuple[str, ...]


# Load one strict requirement manifest and return canonical IDs.
def load_capability_requirements(
    path: str | Path,
) -> CapabilityRequirements:

    try:
        import yaml
    except ImportError as exc:
        raise ValueError("PyYAML is required to load capability requirements") from exc

    manifest_path = Path(path)
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read capability requirements {manifest_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in capability requirements {manifest_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("capability requirements root must be a mapping")
    keys = set(raw)
    if keys != _ROOT_KEYS:
        missing = sorted(_ROOT_KEYS - keys)
        extra = sorted(keys - _ROOT_KEYS)
        raise ValueError(
            f"capability requirements keys are invalid: missing={missing}, extra={extra}"
        )
    if raw["schema"] != SCHEMA:
        raise ValueError(f"unsupported capability requirements schema {raw['schema']!r}")
    suite = raw["suite"]
    if not isinstance(suite, str) or not _SUITE_ID.fullmatch(suite):
        raise ValueError(f"invalid capability requirement suite {suite!r}")

    values = raw["required_capabilities"]
    if not isinstance(values, list) or not values:
        raise ValueError("required_capabilities must be a non-empty list")
    result: list[str] = []
    seen: set[str] = set()
    for index, capability_id in enumerate(values):
        if not isinstance(capability_id, str) or not _CAPABILITY_ID.fullmatch(capability_id):
            raise ValueError(
                f"required_capabilities[{index}] is not a valid capability ID: {capability_id!r}"
            )
        if capability_id in seen:
            raise ValueError(f"required_capabilities repeats {capability_id!r}")
        seen.add(capability_id)
        result.append(capability_id)
    return CapabilityRequirements(suite, tuple(sorted(result)))


# Merge manifests and direct CLI requirements deterministically.
def merge_capability_requirements(
    manifests: Iterable[CapabilityRequirements],
    direct: Iterable[str] = (),
) -> tuple[str, ...]:

    values = set(direct)
    suites: set[str] = set()
    for manifest in manifests:
        if manifest.suite in suites:
            raise ValueError(f"capability requirement suite {manifest.suite!r} is repeated")
        suites.add(manifest.suite)
        values.update(manifest.required_capabilities)
    return tuple(sorted(values))
