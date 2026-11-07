import importlib.util
import struct
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "oot_aspect_probe", Path(__file__).with_name("oot_aspect_probe.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def fixture():
    data = bytearray(0x100 + 0x240)
    data[:4] = b"NSO0"
    # Deliberately unrelated physical offsets and compression flags: a Lichii
    # dump retains these even though its body is a decompressed module image.
    struct.pack_into("<I", data, 0xC, 0x87)
    for i, (location, size) in enumerate(((0, 0x100), (0x100, 0x100), (0x200, 0x40))):
        struct.pack_into("<III", data, 0x10 + i * 0x10, 0x5000 + i * 0x100, location, size)
    data[0x40:0x60] = bytes(range(32))
    return data


class AspectProbeTests(unittest.TestCase):
    def test_dump_layout_and_forward_literal_reference(self):
        data = fixture()
        struct.pack_into("<f", data, 0x100 + 0x140, 16 / 9)
        pc, target = 0x20, 0x140
        struct.pack_into("<I", data, 0x100 + pc, 0x1C000000 | ((target - pc) // 4 << 5))
        report = probe.survey(data)
        self.assertEqual(report["build_id"], bytes(range(32)).hex().upper())
        self.assertEqual(len(report["candidates"]), 1)
        candidate = report["candidates"][0]
        self.assertEqual(candidate["module_offset"], "0x140")
        self.assertEqual(candidate["dump_offset"], "0x240")
        self.assertEqual(candidate["direct_literal_loads"], ["0x20"])
        self.assertAlmostEqual(candidate["target_if_verified"], 422 / 195)

    def test_signed_literal_reference_and_inverse_double(self):
        data = fixture()
        struct.pack_into("<d", data, 0x100, 9 / 16)
        # LDR D0, pc-0x80
        struct.pack_into("<I", data, 0x180, 0x5C000000 | (((-0x80 // 4) & 0x7FFFF) << 5))
        candidate = probe.survey(data)["candidates"][0]
        self.assertEqual(candidate["encoding"], "f64")
        self.assertEqual(candidate["direct_literal_loads"], ["0x80"])
        self.assertAlmostEqual(candidate["target_if_verified"], 195 / 422)

    def test_truncated_and_overlapping_segments_rejected(self):
        data = fixture()
        with self.assertRaises(ValueError):
            probe.survey(data[:-1])
        struct.pack_into("<I", data, 0x24, 0x80)
        with self.assertRaises(ValueError):
            probe.survey(data)

    def test_exact_phone_ratio_and_projection_correction(self):
        target = probe.survey(fixture())["target"]
        self.assertAlmostEqual(target["horizontal_projection_scale_relative_to_16_9"], 520 / 633)
        self.assertEqual(probe.survey(fixture())["candidates"], [])


if __name__ == "__main__":
    unittest.main()
