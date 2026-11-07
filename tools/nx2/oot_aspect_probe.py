#!/usr/bin/env python3
"""Read-only aspect literal survey of Lichii's Dump Decompressed NSOs output.

This identifies investigation candidates, not verified patch addresses. No game
bytes or instruction windows are copied into the JSON report.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


WIDTH, HEIGHT = 2532, 1170
HEADER_SIZE = 0x100


def segments(data):
    if len(data) < HEADER_SIZE or data[:4] != b"NSO0":
        raise ValueError("expected a Lichii decompressed NSO dump with an NSO0 header")
    result = []
    for index, name in enumerate(("text", "rodata", "data")):
        # Lichii dumps header + module memory image, retaining the original
        # NSO flags/file offsets. Do not interpret it as an ordinary NSO file.
        _, location, size = struct.unpack_from("<III", data, 0x10 + index * 0x10)
        if location + size > len(data) - HEADER_SIZE:
            raise ValueError(f"{name} lies outside the dump; use Dump Decompressed NSOs")
        if index and location < result[-1][1] + result[-1][2]:
            raise ValueError("overlapping or unordered module segments")
        result.append((name, location, size))
    return result


def literal_loads(data, text, candidates):
    """Direct AArch64 LDR S/D literal references only; not a full xref analysis."""
    by_address = {(c["module_offset"], c["encoding"]): c for c in candidates}
    _, start, size = text
    for pc in range(start, start + size - 3, 4):
        word = struct.unpack_from("<I", data, HEADER_SIZE + pc)[0]
        opcode = word & 0xFF000000
        if opcode not in (0x1C000000, 0x5C000000):
            continue
        imm = (word >> 5) & 0x7FFFF
        if imm & 0x40000:
            imm -= 0x80000
        target = pc + imm * 4
        match = by_address.get((target, "f32" if opcode == 0x1C000000 else "f64"))
        if match is not None:
            match["direct_literal_loads"].append(hex(pc))


def survey(data):
    layout = segments(data)
    candidates = []
    for encoding, fmt in (("f32", "<f"), ("f64", "<d")):
        for label, value, replacement in (
            ("width_over_height", 16 / 9, WIDTH / HEIGHT),
            ("height_over_width", 9 / 16, HEIGHT / WIDTH),
        ):
            needle = struct.pack(fmt, value)
            for name, location, size in layout:
                start, end = HEADER_SIZE + location, HEADER_SIZE + location + size
                cursor = start
                while True:
                    found = data.find(needle, cursor, end)
                    if found == -1:
                        break
                    cursor = found + 1
                    offset = found - HEADER_SIZE
                    if offset % len(needle):
                        continue
                    candidates.append({
                        "segment": name,
                        "module_offset": offset,
                        "dump_offset": hex(found),
                        "encoding": encoding,
                        "interpretation_if_verified": label,
                        "original": value,
                        "target_if_verified": replacement,
                        "direct_literal_loads": [],
                    })
    literal_loads(data, layout[0], candidates)
    for candidate in candidates:
        candidate["module_offset"] = hex(candidate["module_offset"])
    return {
        "status": "unverified_candidates_only",
        "build_id": data[0x40:0x60].hex().upper(),
        "dump_sha256": hashlib.sha256(data).hexdigest(),
        "target": {"width": WIDTH, "height": HEIGHT, "aspect": WIDTH / HEIGHT,
                   "horizontal_projection_scale_relative_to_16_9": (16 / 9) / (WIDTH / HEIGHT)},
        "candidates": candidates,
        "limits": [
            "Literals can belong to videos, HUDs, or unrelated calculations.",
            "No hits does not rule out a camera aspect computed at runtime.",
            "References via ADRP/ADD/LDR, computed addresses, or immediates are not decoded.",
            "No executable changes or patch files were generated.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump", type=Path, help="main-<build id>.nso from Dump Decompressed NSOs")
    parser.add_argument("--output", type=Path, required=True, help="new JSON report file")
    args = parser.parse_args()
    try:
        report = survey(args.dump.read_bytes())
        # Refuse to overwrite existing reports or accidentally replace the input.
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    except (OSError, ValueError) as error:
        parser.exit(1, f"error: {error}\n")
    print(f"Wrote {args.output}: {len(report['candidates'])} unverified candidates; no patch applied.")


if __name__ == "__main__":
    main()
