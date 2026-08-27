#!/usr/bin/env python3
# Validate that every Checker diagnostic traces to one active rule Owner and canonical heading.

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "report" / "design" / "rule_owner_catalog.yaml"
QUALITY_ROOT = ROOT / "tools" / "quality"
CODE_RE = re.compile(r"\bET[A-Z]+[0-9]{3}\b")
CODE_PART_RE = re.compile(r"^(?P<prefix>ET[A-Z]+)(?P<number>[0-9]{3})$")
RULE_NUMBER_RE = re.compile(r"^R[0-9]{3}$")
LIFECYCLES = {"draft", "active", "deprecated", "superseded"}
DOCUMENT_ROLES = {
    "kernel",
    "contract",
    "policy",
    "procedure",
    "template",
    "proposal",
    "record",
    "history",
}
OWNER_ROLES = {"kernel", "contract", "policy"}


# Match one diagnostic code against one exact code or inclusive same-prefix range.
def _matches(code: str, pattern: str) -> bool:

    if "-" not in pattern:
        return code == pattern
    low_text, high_text = pattern.split("-", 1)
    low = CODE_PART_RE.fullmatch(low_text)
    high = CODE_PART_RE.fullmatch(high_text)
    current = CODE_PART_RE.fullmatch(code)
    if low is None or high is None or current is None:
        return False
    if low.group("prefix") != high.group("prefix") or current.group("prefix") != low.group(
        "prefix"
    ):
        return False
    value = int(current.group("number"))
    return int(low.group("number")) <= value <= int(high.group("number"))


# Expand one bounded namespace for deterministic overlap checks.
def _namespace_codes(pattern: str) -> set[str]:

    if "-" not in pattern:
        return {pattern} if CODE_PART_RE.fullmatch(pattern) else set()
    low_text, high_text = pattern.split("-", 1)
    low = CODE_PART_RE.fullmatch(low_text)
    high = CODE_PART_RE.fullmatch(high_text)
    if low is None or high is None or low.group("prefix") != high.group("prefix"):
        return set()
    low_value = int(low.group("number"))
    high_value = int(high.group("number"))
    if low_value > high_value:
        return set()
    return {f"{low.group('prefix')}{value:03d}" for value in range(low_value, high_value + 1)}


# Load the static Catalog; malformed YAML is a governance failure rather than an empty rule set.
def _load_catalog() -> dict:

    payload = yaml.safe_load(CATALOG.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("catalog root must be a mapping")
    return payload


# Return all stable diagnostics emitted by each quality Checker source.
def _checker_codes() -> dict[str, set[str]]:

    values: dict[str, set[str]] = {}
    for path in sorted(QUALITY_ROOT.glob("*.py")):
        if path.name.startswith("__"):
            continue
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            relative = path.name
        values[relative] = set(CODE_RE.findall(path.read_text(encoding="utf-8-sig")))
    return values


# Return current normative Markdown sources; per-IP contract instances are intentionally excluded.
def _normative_markdown_sources() -> tuple[Path, ...]:

    sources = [ROOT / "AGENTS.md"]
    sources.extend(sorted((ROOT / "report" / "design").rglob("*.md")))
    return tuple(path for path in sources if path.is_file())


# Validate one Owner's diagnostic namespaces and register their exclusive ownership.
def _validate_owner_diagnostics(
    owner: str, diagnostics: object, namespace_owner: dict[str, str]
) -> list[str]:

    if diagnostics is None:
        diagnostics = []
    if not isinstance(diagnostics, list):
        return [f"ETGOV107 {owner}: diagnostics must be a list"]
    if not all(isinstance(item, str) and item for item in diagnostics):
        return [f"ETGOV107 {owner}: invalid diagnostic pattern"]
    errors: list[str] = []
    for pattern in diagnostics:
        expanded = _namespace_codes(pattern)
        if not expanded:
            errors.append(f"ETGOV107 {owner}: invalid diagnostic namespace {pattern!r}")
            continue
        for code in expanded:
            prior = namespace_owner.get(code)
            if prior is not None and prior != owner:
                errors.append(
                    f"ETGOV107 diagnostic namespace {code} overlaps Owners {prior} / {owner}"
                )
            namespace_owner[code] = owner
    return errors


# Validate one Owner's declared Checker files.
def _validate_owner_checkers(owner: str, checkers: object) -> list[str]:

    if checkers is None:
        checkers = []
    if not isinstance(checkers, list):
        return [f"ETGOV108 {owner}: checkers must be a list"]
    return [
        f"ETGOV108 {owner}: Checker does not exist: {checker!r}"
        for checker in checkers
        if not isinstance(checker, str) or not (ROOT / checker).is_file()
    ]


# Validate behavior-regression files for Contracts that do not need a static Checker.
def _validate_owner_tests(owner: str, tests: object) -> list[str]:

    if tests is None:
        tests = []
    if not isinstance(tests, list):
        return [f"ETGOV108 {owner}: tests must be a list"]
    return [
        f"ETGOV108 {owner}: regression test does not exist: {test!r}"
        for test in tests
        if not isinstance(test, str) or not (ROOT / test).is_file()
    ]


# Register one active Owner and validate its canonical source and namespaces.
def _validate_active_owner(
    entry: dict,
    *,
    index: int,
    active_owner_ids: set[str],
    active_rule_ids: set[str],
    namespace_owner: dict[str, str],
) -> list[str]:

    errors: list[str] = []
    owner = entry.get("id")
    rule_id = entry.get("rule_id")
    if not isinstance(owner, str) or not owner:
        return [f"ETGOV105 owner #{index}: missing stable id"]
    if owner in active_owner_ids:
        errors.append(f"ETGOV105 duplicate active Owner: {owner}")
    active_owner_ids.add(owner)
    if not isinstance(rule_id, str) or not rule_id:
        errors.append(f"ETGOV105 {owner}: missing rule_id")
    elif rule_id in active_rule_ids:
        errors.append(f"ETGOV105 duplicate active rule_id: {rule_id}")
    active_rule_ids.add(rule_id)

    source_value = entry.get("source")
    heading = entry.get("heading")
    source = ROOT / str(source_value)
    if not source.is_file():
        errors.append(f"ETGOV106 {owner}: canonical source does not exist: {source_value}")
    elif not isinstance(heading, str) or heading not in source.read_text(encoding="utf-8-sig"):
        errors.append(f"ETGOV106 {owner}: canonical heading does not exist: {heading!r}")

    errors.extend(_validate_owner_diagnostics(owner, entry.get("diagnostics"), namespace_owner))
    errors.extend(_validate_owner_checkers(owner, entry.get("checkers")))
    errors.extend(_validate_owner_tests(owner, entry.get("tests")))
    if not entry.get("checkers") and not entry.get("tests"):
        errors.append(f"ETGOV108 {owner}: at least one Checker or regression test is required")
    return errors


# Validate every emitted diagnostic against the active Owner entries.
def _validate_diagnostic_traceability(active_entries: list[dict]) -> list[str]:

    errors: list[str] = []
    checkers_by_code: dict[str, set[str]] = defaultdict(set)
    for checker, codes in _checker_codes().items():
        for code in codes:
            checkers_by_code[code].add(checker)
    for code, checkers in sorted(checkers_by_code.items()):
        if len(checkers) != 1:
            errors.append(
                f"ETGOV109 diagnostic {code} is emitted by multiple Checkers: "
                + ", ".join(sorted(checkers))
            )
        matches = [
            entry
            for entry in active_entries
            if any(_matches(code, pattern) for pattern in entry.get("diagnostics", []))
        ]
        if len(matches) != 1:
            errors.append(f"ETGOV109 diagnostic {code} maps to {len(matches)} active Owners")
            continue
        declared = set(matches[0].get("checkers", []))
        if not set(checkers).issubset(declared):
            errors.append(
                f"ETGOV109 diagnostic {code} Checker is not declared by Owner "
                f"{matches[0].get('id')}"
            )
    return errors


# Prevent an optional machine-contract marker from becoming a second normative rule body.
def _validate_exclusive_rule_markers(active_entries: list[dict]) -> list[str]:

    errors: list[str] = []
    normative_sources = _normative_markdown_sources()
    for entry in active_entries:
        markers = entry.get("exclusive_markers")
        if markers is None:
            continue
        owner = entry.get("id")
        source = ROOT / str(entry.get("source"))
        if not isinstance(markers, list) or not all(
            isinstance(marker, str) and marker for marker in markers
        ):
            errors.append(f"ETGOV110 {owner}: exclusive_markers must be a non-empty string list")
            continue
        for marker in markers:
            locations = [
                path for path in normative_sources if marker in path.read_text(encoding="utf-8-sig")
            ]
            if locations != [source]:
                rendered = ", ".join(path.relative_to(ROOT).as_posix() for path in locations)
                errors.append(
                    f"ETGOV110 {owner}: exclusive marker {marker!r} must appear only in "
                    f"{entry.get('source')}; found [{rendered}]"
                )
    return errors


# Validate replacement routing for one deprecated or superseded document.
def _validate_document_replacement(
    path_value: str, lifecycle: object, replacement: object
) -> list[str]:

    if lifecycle in {"deprecated", "superseded"}:
        if not isinstance(replacement, str) or not replacement:
            return [f"ETGOV117 {path_value}: {lifecycle} document needs superseded_by"]
        if replacement == path_value or not (ROOT / replacement).is_file():
            return [f"ETGOV117 {path_value}: invalid superseded_by {replacement!r}"]
    elif replacement is not None:
        return [f"ETGOV117 {path_value}: only deprecated/superseded may set superseded_by"]
    return []


# Validate one document's role, lifecycle, Owner binding and replacement target.
def _validate_document_entry(
    entry: object,
    *,
    index: int,
    active_owner_ids: set[str],
    seen_paths: set[str],
) -> list[str]:

    if not isinstance(entry, dict):
        return [f"ETGOV111 document #{index} must be a mapping"]
    errors: list[str] = []
    path_value = entry.get("path")
    if not isinstance(path_value, str) or not path_value.startswith("report/design/"):
        return [f"ETGOV112 document #{index}: invalid report/design path {path_value!r}"]
    if path_value in seen_paths:
        errors.append(f"ETGOV113 duplicate document inventory path: {path_value}")
    seen_paths.add(path_value)
    path = ROOT / path_value
    if not path.is_file() or path.suffix.lower() != ".md":
        errors.append(f"ETGOV112 inventory document does not exist: {path_value}")

    role = entry.get("role")
    lifecycle = entry.get("lifecycle")
    if role not in DOCUMENT_ROLES:
        errors.append(f"ETGOV114 {path_value}: invalid document role {role!r}")
    if lifecycle not in LIFECYCLES:
        errors.append(f"ETGOV115 {path_value}: invalid document lifecycle {lifecycle!r}")

    owners = entry.get("owners", [])
    if not isinstance(owners, list) or not all(
        isinstance(owner, str) and owner for owner in owners
    ):
        errors.append(f"ETGOV116 {path_value}: owners must be a string list")
        owners = []
    unknown_owners = sorted(set(owners) - active_owner_ids)
    if unknown_owners:
        errors.append(f"ETGOV116 {path_value}: unknown active Owners {unknown_owners}")
    if role in OWNER_ROLES and lifecycle == "active" and not owners:
        errors.append(f"ETGOV116 {path_value}: active {role} requires at least one Owner")
    if role not in OWNER_ROLES and owners:
        errors.append(f"ETGOV116 {path_value}: role {role} must not claim rule Owners")
    if lifecycle != "active" and owners:
        errors.append(f"ETGOV116 {path_value}: non-active document must not claim rule Owners")

    errors.extend(_validate_document_replacement(path_value, lifecycle, entry.get("superseded_by")))
    return errors


# Require every report/design Markdown file to have exactly one machine-readable role record.
def _validate_document_inventory(
    payload: dict, active_entries: list[dict], active_owner_ids: set[str]
) -> list[str]:

    documents = payload.get("documents")
    if not isinstance(documents, list) or not documents:
        return ["ETGOV111 rule Catalog documents must be a non-empty list"]
    errors: list[str] = []
    seen_paths: set[str] = set()
    for index, entry in enumerate(documents):
        errors.extend(
            _validate_document_entry(
                entry,
                index=index,
                active_owner_ids=active_owner_ids,
                seen_paths=seen_paths,
            )
        )
    expected_paths = {
        path.relative_to(ROOT).as_posix() for path in (ROOT / "report" / "design").rglob("*.md")
    }
    missing = sorted(expected_paths - seen_paths)
    unexpected = sorted(seen_paths - expected_paths)
    if missing:
        errors.append(f"ETGOV113 unregistered report/design documents: {missing}")
    if unexpected:
        errors.append(f"ETGOV113 inventory paths outside current report/design set: {unexpected}")
    inventory = {entry.get("path"): entry for entry in documents if isinstance(entry, dict)}
    for owner_entry in active_entries:
        source = owner_entry.get("source")
        if not isinstance(source, str) or not source.startswith("report/design/"):
            continue
        document = inventory.get(source)
        owner = owner_entry.get("id")
        if (
            not isinstance(document, dict)
            or document.get("role") not in OWNER_ROLES
            or document.get("lifecycle") != "active"
            or owner not in document.get("owners", [])
        ):
            errors.append(
                f"ETGOV116 {owner}: canonical source {source} must be an active "
                "owner-bearing document"
            )
    return errors


# Parse and validate the standard metadata owned by one numbered rule document.
def _load_rule_front_matter(path: Path) -> tuple[dict | None, str | None]:

    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None, "missing opening YAML front matter marker"
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return None, "missing closing YAML front matter marker"
    try:
        metadata = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError as exc:
        return None, f"invalid YAML front matter: {exc}"
    if not isinstance(metadata, dict):
        return None, "front matter must be a mapping"
    return metadata, None


# Enforce stable numbering, the dedicated rules directory and Catalog/front-matter agreement.
def _validate_rule_documents(payload: dict, active_entries: list[dict]) -> list[str]:

    errors: list[str] = []
    source_entries: dict[str, list[dict]] = defaultdict(list)
    number_source: dict[str, str] = {}
    for entry in active_entries:
        owner = entry.get("id")
        number = entry.get("number")
        source = entry.get("source")
        if not isinstance(number, str) or RULE_NUMBER_RE.fullmatch(number) is None:
            errors.append(f"ETGOV118 {owner}: invalid or missing rule number {number!r}")
            continue
        if not isinstance(source, str) or not source.startswith("report/design/rules/"):
            errors.append(f"ETGOV119 {owner}: active rule source must be under report/design/rules")
            continue
        prior = number_source.get(number)
        if prior is not None and prior != source:
            errors.append(
                f"ETGOV122 rule number {number} maps to multiple sources: {prior}, {source}"
            )
        number_source[number] = source
        source_entries[source].append(entry)

    documents = payload.get("documents", [])
    inventory = {entry.get("path"): entry for entry in documents if isinstance(entry, dict)}
    for source, entries in sorted(source_entries.items()):
        path = ROOT / source
        if not path.is_file():
            continue
        number = entries[0]["number"]
        if path.parent != ROOT / "report" / "design" / "rules" or not path.name.startswith(
            f"{number}_"
        ):
            errors.append(f"ETGOV119 {source}: filename must start with {number}_ in rules/")
        metadata, metadata_error = _load_rule_front_matter(path)
        if metadata_error is not None:
            errors.append(f"ETGOV120 {source}: {metadata_error}")
            continue
        expected_owners = sorted(str(entry["id"]) for entry in entries)
        expected_rule_ids = sorted(str(entry["rule_id"]) for entry in entries)
        metadata_owners = metadata.get("owners")
        metadata_rule_ids = metadata.get("rule_ids")
        if (
            metadata.get("schema") != "et.rule-document.v1"
            or metadata.get("number") != number
            or not isinstance(metadata.get("domain"), str)
            or not metadata.get("domain")
            or metadata.get("lifecycle") != "active"
            or not isinstance(metadata_owners, list)
            or not all(isinstance(item, str) for item in metadata_owners)
            or sorted(metadata_owners) != expected_owners
            or not isinstance(metadata_rule_ids, list)
            or not all(isinstance(item, str) for item in metadata_rule_ids)
            or sorted(metadata_rule_ids) != expected_rule_ids
        ):
            errors.append(f"ETGOV121 {source}: front matter does not match active Owner Catalog")
        document = inventory.get(source)
        if not isinstance(document, dict) or document.get("number") != number:
            errors.append(f"ETGOV121 {source}: document inventory number must be {number}")
        body = path.read_text(encoding="utf-8-sig")
        if f"# {number} " not in body:
            errors.append(f"ETGOV121 {source}: title must start with '# {number} '")
        if len(body.splitlines()) > 400:
            errors.append(f"ETGOV121 {source}: active rule document exceeds 400 lines")

    registered_sources = set(source_entries)
    actual_rule_files = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "report" / "design" / "rules").rglob("*.md")
    }
    unregistered = sorted(actual_rule_files - registered_sources)
    if unregistered:
        errors.append(f"ETGOV123 unregistered active rule files: {unregistered}")
    return errors


# Validate Owner uniqueness, source anchors, Checker paths and diagnostic traceability.
def validate_governance() -> list[str]:

    try:
        payload = _load_catalog()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"ETGOV101 {CATALOG.name}: invalid rule Catalog: {exc}"]

    errors: list[str] = []
    if payload.get("schema") != "et.rule-owner-catalog.v1":
        errors.append("ETGOV102 rule Catalog schema must be et.rule-owner-catalog.v1")
    owners = payload.get("owners")
    if not isinstance(owners, list) or not owners:
        return [*errors, "ETGOV103 rule Catalog owners must be a non-empty list"]

    active_owner_ids: set[str] = set()
    active_rule_ids: set[str] = set()
    active_entries: list[dict] = []
    namespace_owner: dict[str, str] = {}
    for index, entry in enumerate(owners):
        if not isinstance(entry, dict):
            errors.append(f"ETGOV103 owner #{index} must be a mapping")
            continue
        lifecycle = entry.get("lifecycle")
        if lifecycle not in LIFECYCLES:
            errors.append(f"ETGOV104 {entry.get('id') or index}: invalid lifecycle {lifecycle!r}")
            continue
        if lifecycle != "active":
            continue
        active_entries.append(entry)
        errors.extend(
            _validate_active_owner(
                entry,
                index=index,
                active_owner_ids=active_owner_ids,
                active_rule_ids=active_rule_ids,
                namespace_owner=namespace_owner,
            )
        )

    errors.extend(_validate_diagnostic_traceability(active_entries))
    errors.extend(_validate_exclusive_rule_markers(active_entries))
    errors.extend(_validate_document_inventory(payload, active_entries, active_owner_ids))
    errors.extend(_validate_rule_documents(payload, active_entries))

    return sorted(set(errors))


def main() -> int:

    errors = validate_governance()
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"Rule governance validation failed: {len(errors)} violation(s).", file=sys.stderr)
        return 1
    print("Rule governance validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
