# 根据声明式清单生成可复现的 Keil 工程，不承担固件编译或硬件烧写。

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _required_text(parent: ET.Element, path: str) -> ET.Element:
    element = parent.find(path)
    if element is None:
        raise ValueError(f"Keil template is missing XML node: {path}")
    return element


def _windows_relative(path: Path, base: Path) -> str:
    return os.path.relpath(path.resolve(), base.resolve()).replace("/", "\\")


def _file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".c":
        return "1"
    if suffix in {".s", ".asm"}:
        return "2"
    if suffix in {".h", ".hpp"}:
        return "5"
    raise ValueError(f"Unsupported Keil source type: {path}")


def _add_group(
    groups: ET.Element,
    name: str,
    paths: list[Path],
    output_directory: Path,
    target: ET.Element,
    disabled_paths: set[Path] | None = None,
) -> None:
    group = ET.SubElement(groups, "Group")
    ET.SubElement(group, "GroupName").text = name
    files = ET.SubElement(group, "Files")
    inactive = disabled_paths or set()
    for path in paths:
        file_element = ET.SubElement(files, "File")
        ET.SubElement(file_element, "FileName").text = path.name
        file_type = _file_type(path)
        ET.SubElement(file_element, "FileType").text = file_type
        ET.SubElement(file_element, "FilePath").text = _windows_relative(path, output_directory)
        if path in inactive:
            _disable_file_for_target(file_element, target, file_type)


# Keep one deterministic file universe while excluding target-owned variants.
def _disable_file_for_target(
    file_element: ET.Element,
    target: ET.Element,
    file_type: str,
) -> None:
    file_option = ET.SubElement(file_element, "FileOption")
    common = copy.deepcopy(_required_text(target, "TargetOption/CommonProperty"))
    _required_text(common, "IncludeInBuild").text = "0"
    file_option.append(common)

    arm_options = ET.SubElement(file_option, "FileArmAds")
    option_name = "Aads" if file_type == "2" else "Cads"
    option = copy.deepcopy(_required_text(target, f"TargetOption/TargetArmAds/{option_name}"))
    arm_options.append(option)


# Apply chip-owned Keil device facts without hard-coding a chip here.
def _apply_keil_device_profile(
    target: ET.Element,
    profile: dict[str, object],
) -> None:
    common = _required_text(target, "TargetOption/TargetCommonOption")
    common_fields = {
        "vendor": "Vendor",
        "pack_id": "PackID",
        "pack_url": "PackURL",
        "cpu": "Cpu",
        "register_file": "RegisterFile",
        "sfd_file": "SFDFile",
        "custom_svd": "bCustSvd",
    }
    for profile_name, xml_name in common_fields.items():
        if profile_name in profile:
            _required_text(common, xml_name).text = str(profile[profile_name])

    if "invalid_flash" in profile:
        _required_text(common, "TargetStatus/InvalidFlash").text = str(profile["invalid_flash"])
    if "update_flash_before_debugging" in profile:
        _required_text(
            target,
            "TargetOption/Utilities/Flash1/UpdateFlashBeforeDebugging",
        ).text = str(profile["update_flash_before_debugging"])


def _resolve_files(
    groups: dict[str, list[str]],
    root: Path,
) -> dict[str, list[Path]]:
    resolved: dict[str, list[Path]] = {}
    for group_name, entries in groups.items():
        paths = [(root / entry).resolve() for entry in entries]
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"{group_name} references missing files: {missing}")
        resolved[group_name] = paths
    return resolved


def _generate_options(
    manifest: dict[str, object],
    template_root: Path,
    output_path: Path,
    effective_flash_drivers: dict[str, str],
) -> tuple[Path, str]:
    template_entry = manifest.get("template_options")
    if not template_entry:
        raise ValueError("Project manifest has no template_options")
    template_path = (template_root / str(template_entry)).resolve()
    if not template_path.is_file():
        raise FileNotFoundError(f"Keil options template not found: {template_path}")

    tree = ET.parse(template_path)
    root = tree.getroot()
    option_targets = root.findall("Target")
    templates = {_required_text(target, "TargetName").text: target for target in option_targets}
    if not option_targets:
        raise ValueError(f"Keil options template has no Target nodes: {template_path}")
    insert_at = list(root).index(option_targets[0])
    for target in option_targets:
        root.remove(target)

    for offset, target_spec in enumerate(manifest["targets"]):
        template_name = target_spec["template_target"]
        if template_name not in templates:
            raise ValueError(
                f"Options template target {template_name!r} was not found in {template_path}"
            )
        target = copy.deepcopy(templates[template_name])
        target_name = target_spec["name"]
        _required_text(target, "TargetName").text = target_name
        target_option = _required_text(target, "TargetOption")
        registry_entries = {
            entry.findtext("Key"): entry
            for entry in target_option.findall("TargetDriverDllRegistry/SetRegEntry")
        }
        debug_driver = str(target_spec.get("debug_driver", "ulink")).lower()
        if debug_driver == "jlink":
            ulink_entry = registry_entries.get("UL2CM3")
            jlink_entry = registry_entries.get("JL2CM3")
            if ulink_entry is None or jlink_entry is None:
                raise ValueError(
                    f"Options target {template_name!r} has no UL2CM3/JL2CM3 registry entries"
                )
            _required_text(ulink_entry, "Name").text = effective_flash_drivers[target_name]
            loader_args = str(target_spec.get("jlink_flash_loader_args", "")).strip()
            if loader_args:
                jlink_name = _required_text(jlink_entry, "Name")
                base = re.sub(
                    r"\s+-FN\d+\b.*$",
                    "",
                    jlink_name.text or "",
                ).rstrip()
                jlink_name.text = f"{base} {loader_args}"
            _required_text(target_option, "DebugOpt/pMon").text = r"Segger\JL2CM3.dll"
            # The probe/device route comes from JLinkSettings.ini. Do not add
            # ULINK DebugDescription fields to a J-Link target.
            debug_description = target_option.find("DebugDescription")
            if debug_description is not None:
                target_option.remove(debug_description)
        elif debug_driver == "ulink":
            ulink_entry = registry_entries.get("UL2CM3")
            if ulink_entry is None:
                raise ValueError(f"Options target {template_name!r} has no UL2CM3 registry entry")
            _required_text(ulink_entry, "Name").text = effective_flash_drivers[target_name]
            _required_text(target_option, "DebugOpt/pMon").text = r"BIN\UL2CM3.DLL"
            debug_description = target_option.find("DebugDescription")
            if debug_description is None:
                debug_description = ET.SubElement(target_option, "DebugDescription")
            protocol_name = str(target_spec.get("debug_protocol", "jtag")).lower()
            protocol_value = {"swd": "1", "jtag": "2"}.get(protocol_name)
            if protocol_value is None:
                raise ValueError(f"Unsupported debug_protocol: {protocol_name}")
            debug_values = {
                "Enable": "1",
                "EnableFlashSeq": "1",
                "EnableLog": "0",
                "Protocol": protocol_value,
                "DbgClock": str(int(target_spec.get("debug_clock_hz", 1_000_000))),
            }
            for name, value in debug_values.items():
                node = debug_description.find(name)
                if node is None:
                    node = ET.SubElement(debug_description, name)
                node.text = value
        else:
            raise ValueError(f"Unsupported debug_driver: {debug_driver}")

        current_target = target_option.find("OPTFL/IsCurrentTarget")
        if current_target is not None:
            current_target.text = "1" if offset == 0 else "0"
        root.insert(insert_at + offset, target)

    options_path = output_path.with_suffix(".uvoptx")
    ET.indent(tree, space="  ")
    tree.write(options_path, encoding="utf-8", xml_declaration=True)
    return options_path, hashlib.sha256(options_path.read_bytes()).hexdigest()


def generate(
    manifest_path: Path,
    sdk_root: Path | None,
    output_override: Path | None,
) -> tuple[Path, dict[str, object]]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Only project manifest schema_version 1 is supported")

    template_root_kind = str(manifest.get("template_root", "sdk"))
    if template_root_kind == "manifest":
        template_root = manifest_path.resolve().parent
    elif template_root_kind == "project":
        template_root = PROJECT_ROOT
    elif template_root_kind == "sdk":
        if sdk_root is None:
            raise ValueError("The manifest requires an SDK root for its Keil template")
        template_root = sdk_root.resolve()
    else:
        raise ValueError(f"Unsupported template_root: {template_root_kind}")

    template_path = (template_root / str(manifest["template_project"])).resolve()
    if not template_path.is_file():
        raise FileNotFoundError(f"Keil template not found: {template_path}")

    output_path = (
        output_override.resolve()
        if output_override is not None
        else (PROJECT_ROOT / manifest["output_project"]).resolve()
    )
    output_directory = output_path.parent

    project_groups = _resolve_files(manifest.get("project_groups", {}), PROJECT_ROOT)
    target_project_groups = {
        target_spec["name"]: _resolve_files(target_spec.get("project_groups", {}), PROJECT_ROOT)
        for target_spec in manifest["targets"]
    }
    target_group_universe: dict[str, list[Path]] = {}
    for groups in target_project_groups.values():
        for group_name, paths in groups.items():
            universe_paths = target_group_universe.setdefault(group_name, [])
            for path in paths:
                if path not in universe_paths:
                    universe_paths.append(path)
    sdk_group_entries = manifest.get("sdk_groups", {})
    sdk_include_entries = manifest.get("sdk_includes", [])
    if (sdk_group_entries or sdk_include_entries) and sdk_root is None:
        raise ValueError("The manifest contains sdk_groups/sdk_includes but no SDK root")
    sdk_groups = _resolve_files(sdk_group_entries, sdk_root) if sdk_root is not None else {}
    project_includes = [
        (PROJECT_ROOT / entry).resolve() for entry in manifest.get("project_includes", [])
    ]
    target_project_includes = {
        target_spec["name"]: [
            (PROJECT_ROOT / entry).resolve() for entry in target_spec.get("project_includes", [])
        ]
        for target_spec in manifest["targets"]
    }
    sdk_includes = (
        [(sdk_root / entry).resolve() for entry in sdk_include_entries]
        if sdk_root is not None
        else []
    )
    missing_includes = [
        str(path)
        for path in (
            project_includes
            + sdk_includes
            + [include for includes in target_project_includes.values() for include in includes]
        )
        if not path.is_dir()
    ]
    if missing_includes:
        raise FileNotFoundError(
            f"Project manifest references missing include paths: {missing_includes}"
        )

    tree = ET.parse(template_path)
    root = tree.getroot()
    targets = _required_text(root, "Targets")
    template_targets = {
        _required_text(target, "TargetName").text: target for target in targets.findall("Target")
    }
    targets.clear()

    generated_targets: list[dict[str, object]] = []
    effective_flash_drivers: dict[str, str] = {}
    for target_spec in manifest["targets"]:
        template_name = target_spec["template_target"]
        if template_name not in template_targets:
            raise ValueError(f"Template target {template_name!r} was not found in {template_path}")
        target = copy.deepcopy(template_targets[template_name])
        _required_text(target, "TargetName").text = target_spec["name"]
        common = _required_text(target, "TargetOption/TargetCommonOption")
        _required_text(common, "Device").text = manifest["device"]
        device_profile = target_spec.get("keil_device_profile")
        if device_profile:
            _apply_keil_device_profile(target, device_profile)
        _required_text(common, "OutputDirectory").text = target_spec["output_directory"]
        _required_text(common, "OutputName").text = target_spec["output_name"]
        _required_text(common, "CreateExecutable").text = "1"
        _required_text(common, "CreateHexFile").text = "1"
        flash_driver = target_spec.get("flash_driver")
        if flash_driver:
            flash_node = common.find("FlashDriverDll")
            if flash_node is None:
                flash_node = ET.SubElement(common, "FlashDriverDll")
            flash_node.text = flash_driver
        effective_flash_drivers[target_spec["name"]] = (
            _required_text(common, "FlashDriverDll").text or ""
        )

        controls = _required_text(
            target,
            "TargetOption/TargetArmAds/Cads/VariousControls",
        )
        _required_text(controls, "Define").text = ",".join(target_spec["defines"])
        effective_project_includes = project_includes + target_project_includes[target_spec["name"]]
        include_text = ";".join(
            _windows_relative(path, output_directory)
            for path in effective_project_includes + sdk_includes
        )
        _required_text(controls, "IncludePath").text = include_text

        assembler_controls = target.find(
            "TargetOption/TargetArmAds/Aads/VariousControls/IncludePath"
        )
        if assembler_controls is not None:
            assembler_controls.text = ";".join(
                _windows_relative(path, output_directory) for path in sdk_includes
            )

        scatter_root = target_spec.get("scatter_root", "sdk")
        if scatter_root == "project":
            scatter_path = (PROJECT_ROOT / target_spec["scatter_file"]).resolve()
        elif scatter_root == "sdk":
            if sdk_root is None:
                raise ValueError("A target uses scatter_root=sdk but no SDK root was supplied")
            scatter_path = (sdk_root / target_spec["scatter_file"]).resolve()
        else:
            raise ValueError(f"Unsupported scatter_root: {scatter_root}")
        if not scatter_path.is_file():
            raise FileNotFoundError(f"Scatter file not found: {scatter_path}")
        ldads = _required_text(target, "TargetOption/TargetArmAds/LDads")
        _required_text(
            target,
            "TargetOption/TargetArmAds/LDads/ScatterFile",
        ).text = _windows_relative(scatter_path, output_directory)
        # Force "use scatter file" (umfTarg=0). Otherwise Keil ignores the
        # ScatterFile and auto-generates a layout from the target-dialog memory,
        # which for the Flash target places code in ITCM (0x00000000) and shrinks
        # the RW region so the stack no longer fits.
        umf_targ = ldads.find("umfTarg")
        if umf_targ is None:
            umf_targ = ET.SubElement(ldads, "umfTarg")
        umf_targ.text = "0"

        old_groups = target.find("Groups")
        if old_groups is None:
            old_groups = ET.SubElement(target, "Groups")
        else:
            old_groups.clear()
        for group_name, paths in project_groups.items():
            _add_group(old_groups, group_name, paths, output_directory, target)
        active_target_groups = target_project_groups[target_spec["name"]]
        for group_name, paths in target_group_universe.items():
            active_paths = set(active_target_groups.get(group_name, []))
            _add_group(
                old_groups,
                group_name,
                paths,
                output_directory,
                target,
                disabled_paths=set(paths) - active_paths,
            )
        for group_name, paths in sdk_groups.items():
            _add_group(old_groups, group_name, paths, output_directory, target)

        targets.append(target)
        generated_targets.append(
            {
                "name": target_spec["name"],
                "template_target": template_name,
                "defines": target_spec["defines"],
                "scatter_file": str(scatter_path),
                "project_includes": [
                    str(path) for path in target_project_includes[target_spec["name"]]
                ],
            }
        )

    for optional_node in ("RTE", "LayerInfo"):
        node = root.find(optional_node)
        if node is not None:
            root.remove(node)

    output_directory.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
    support_files: dict[str, dict[str, str]] = {}
    options_path, options_hash = _generate_options(
        manifest,
        template_root,
        output_path,
        effective_flash_drivers,
    )
    support_files["keil_options"] = {
        "source": str((template_root / str(manifest["template_options"])).resolve()),
        "output": str(options_path.resolve()),
        "sha256": options_hash,
    }
    jlink_settings_entry = manifest.get("jlink_settings")
    if jlink_settings_entry:
        jlink_settings_source = (PROJECT_ROOT / jlink_settings_entry).resolve()
        if not jlink_settings_source.is_file():
            raise FileNotFoundError(f"J-Link settings template not found: {jlink_settings_source}")
        jlink_settings_output = output_directory / "JLinkSettings.ini"
        shutil.copyfile(jlink_settings_source, jlink_settings_output)
        support_files["jlink_settings"] = {
            "source": str(jlink_settings_source),
            "output": str(jlink_settings_output.resolve()),
            "sha256": hashlib.sha256(jlink_settings_output.read_bytes()).hexdigest(),
        }
    generation_record: dict[str, object] = {
        "schema_version": 1,
        "chip": manifest["chip"],
        "manifest": str(manifest_path.resolve()),
        "template": str(template_path),
        "template_root": str(template_root),
        "sdk_root": (str(sdk_root.resolve()) if sdk_root is not None else None),
        "output": str(output_path),
        "sha256": digest,
        "targets": generated_targets,
        "support_files": support_files,
    }
    record_path = output_path.with_suffix(".generation.json")
    record_path.write_text(
        json.dumps(generation_record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path, generation_record


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Generate a lightweight Keil project from a local or SDK template.")
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--sdk-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    sdk_root = args.sdk_root
    requires_sdk_root = (
        str(manifest.get("template_root", "sdk")) == "sdk"
        or bool(manifest.get("sdk_groups"))
        or bool(manifest.get("sdk_includes"))
        or any(
            str(target.get("scatter_root", "sdk")) == "sdk"
            for target in manifest.get("targets", [])
        )
    )
    if sdk_root is None and requires_sdk_root:
        environment_name = manifest.get("sdk_environment")
        if not environment_name:
            parser.error("The manifest requires an SDK root but has no sdk_environment")
        environment_value = os.environ.get(environment_name)
        if not environment_value:
            parser.error(f"Pass --sdk-root or define {environment_name}")
        sdk_root = Path(environment_value)

    output, record = generate(args.manifest, sdk_root, args.output)
    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output),
                "sha256": record["sha256"],
                "targets": [
                    item["name"]
                    for item in record["targets"]  # type: ignore[index]
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
