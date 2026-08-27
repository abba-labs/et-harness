# Materialize host-local validation files for committed Keil artifacts.
#
# This tool does not build firmware and does not regenerate the project from SDK
# sources. It copies the committed options template when the build-directory copy
# is absent, creates deterministic J-Link settings, and records hashes/resolved
# host paths so repository contract tests can run on any host. Actual Keil build
# evidence remains a separate later-stage requirement.

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections.abc import Sequence
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_JLINK_SETTINGS = """[FLASH]
Override = 1
Device=\"Cortex-M7\"
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{label} is missing: {resolved}")
    return resolved


# Write host-local support files and a validation record for Keil artifacts.
def materialize(manifest_path: Path) -> Path:

    resolved_manifest = _require_file(manifest_path, "firmware manifest")
    manifest = yaml.safe_load(resolved_manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("firmware manifest must contain a mapping")

    template_root_mode = str(manifest.get("template_root", "sdk"))
    if template_root_mode != "manifest":
        raise ValueError("validation record materialization requires template_root=manifest")

    template_root = resolved_manifest.parent.resolve()
    template = _require_file(
        template_root / str(manifest["template_project"]),
        "Keil template project",
    )
    options_template = _require_file(
        template_root / str(manifest["template_options"]),
        "Keil options template",
    )
    project = _require_file(
        PROJECT_ROOT / str(manifest["output_project"]),
        "committed Keil project",
    )

    options = project.with_suffix(".uvoptx").resolve()
    if not options.is_file():
        shutil.copyfile(options_template, options)

    jlink_settings = (project.parent / "JLinkSettings.ini").resolve()
    if not jlink_settings.is_file():
        jlink_settings.write_text(_JLINK_SETTINGS, encoding="utf-8")

    record = {
        "schema_version": 1,
        "record_kind": "committed-artifact-validation",
        "chip": str(manifest["chip"]),
        "manifest": str(resolved_manifest),
        "template": str(template),
        "template_root": str(template_root),
        "sdk_root": None,
        "output": str(project),
        "sha256": _sha256(project),
        "targets": [],
        "support_files": {
            "keil_options": {
                "output": str(options),
                "sha256": _sha256(options),
            },
            "jlink_settings": {
                "output": str(jlink_settings),
                "sha256": _sha256(jlink_settings),
            },
        },
    }
    record_path = project.with_suffix(".generation.json")
    record_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return record_path


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize one Keil validation record.")
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args(argv)


# Materialize validation files and print the record path for CI logs.
def main(argv: Sequence[str] | None = None) -> int:

    args = _parse_args(argv)
    record_path = materialize(args.manifest)
    print(record_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
