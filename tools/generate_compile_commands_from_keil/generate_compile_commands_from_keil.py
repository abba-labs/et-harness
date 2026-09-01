from pathlib import Path
import json
import xml.etree.ElementTree as ET

UVPROJX = Path("firmware/build/et6801/ET6801_Automated_Test.uvprojx")
OUT = Path("firmware/build/et6801/compile_commands.json")

tree = ET.parse(UVPROJX)
root = tree.getroot()

project_dir = UVPROJX.parent.resolve()

define_node = root.find(".//Define")
include_node = root.find(".//IncludePath")

defines = []
if define_node is not None and define_node.text:
    defines = [x.strip() for x in define_node.text.split(",") if x.strip()]

include_paths = []
if include_node is not None and include_node.text:
    include_paths = [x.strip() for x in include_node.text.split(";") if x.strip()]

compile_commands = []

for file_node in root.findall(".//FilePath"):
    if not file_node.text:
        continue

    rel_file = file_node.text.strip()

    if not rel_file.lower().endswith((".c", ".cpp", ".cc", ".cxx")):
        continue

    src = (project_dir / rel_file).resolve()

    args = [
        "clang",
        "-x",
        "c",
        "-std=c11",
        "-isystem",
        r"C:\Keil_v5\ARM\ARMCLANG\include",
        "-isystem",
        r"C:\Keil_v5\ARM\ARMCLANG\lib\clang\13.0.0\include",
    ]

    for define in defines:
        args.append(f"-D{define}")

    for inc in include_paths:
        inc_abs = (project_dir / inc).resolve()
        args.extend(["-I", str(inc_abs)])

    args.append(str(src))

    compile_commands.append(
        {
            "directory": str(project_dir),
            "file": str(src),
            "arguments": args,
        }
    )

OUT.write_text(
    json.dumps(compile_commands, indent=2),
    encoding="utf-8",
)

print(f"Generated: {OUT}")
print(f"Source files: {len(compile_commands)}")
