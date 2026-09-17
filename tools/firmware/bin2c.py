#!/usr/bin/env python3
"""Convert a compiled binary image into a C header with a const uint8_t array."""

from __future__ import annotations

import argparse
from pathlib import Path


def bin_to_c_header(
    bin_path: Path, output_header: Path, symbol_name: str = "g_core1_image"
) -> None:
    data = bin_path.read_bytes()
    macro_guard = f"__{output_header.stem.upper()}_H"

    lines = [
        "/* Automatically generated binary image array - DO NOT EDIT */",
        f"#ifndef {macro_guard}",
        f"#define {macro_guard}",
        "",
        "#include <stdint.h>",
        "",
        f"#define ET_CORE1_IMAGE_SIZE ({len(data)}u)",
        "",
        f"static const uint8_t {symbol_name}[ET_CORE1_IMAGE_SIZE] = {{",
    ]

    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        hex_str = ", ".join(f"0x{b:02X}u" for b in chunk)
        lines.append(f"    {hex_str},")

    lines.append("};")
    lines.append("")
    lines.append(f"#endif /* {macro_guard} */")
    lines.append("")

    output_header.parent.mkdir(parents=True, exist_ok=True)
    output_header.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {output_header} from {bin_path} ({len(data)} bytes).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert binary file to C header array")
    parser.add_argument("bin_path", type=Path, help="Path to input .bin file")
    parser.add_argument("output_header", type=Path, help="Path to output .h header file")
    parser.add_argument("--symbol", default="g_core1_image", help="Array symbol name")
    args = parser.parse_args()
    bin_to_c_header(args.bin_path, args.output_header, args.symbol)


if __name__ == "__main__":
    main()
