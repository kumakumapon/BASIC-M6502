import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from convert import Converter
from font import make_font


class BuildTests(unittest.TestCase):
    def test_radix_character_and_six_character_symbols(self):
        c = Converter()
        c.radix = 8
        self.assertEqual(c.expr("201"), "129")
        self.assertEqual(c.expr("^D255"), "255")
        self.assertEqual(c.expr('"8"'), "56")
        self.assertEqual(c.expr("8*ADDPRC+230"), "8*B_ADDPRC+152")
        self.assertEqual(c.expr("RESTORE-1"), "B_RESTOR-1")
        self.assertEqual(c.expr("<<12345>&^O377>"), "((5349)&255)")

    def test_translation_is_deterministic_and_has_full_math_package(self):
        source = (ROOT / "m6502.asm").read_text()
        result = Converter().run(source)
        self.assertEqual(result, Converter().run(source))
        self.assertIn("B_ATN:", result)
        self.assertIn("B_FDIVT:", result)
        self.assertIn("B_INIT:", result)
        self.assertNotIn("B_LOOPMM:", result)
        self.assertNotIn("lda #<(B_MEMORY)", result)
        self.assertIn("B_LINLEN .set 32", result)
        self.assertIn("B_STKEND .set 507", result)
        self.assertEqual(result, (ROOT / "build/basic.s").read_text())

    def test_rom_header_and_vectors(self):
        rom = (ROOT / "build/basic.nes").read_bytes()
        self.assertEqual(len(rom), 16 + 32768 + 8192)
        self.assertEqual(
            rom[:16], b"NES\x1a\x02\x01\x10\x08\x00\x00\x07\x00\x00\x00\x00\x23"
        )
        for offset in range(0x7FFA, 0x8000, 2):
            vector = int.from_bytes(rom[16 + offset : 18 + offset], "little")
            self.assertTrue(0xC000 <= vector < 0xFFFA)
        self.assertEqual(rom[-8192:], make_font())


if __name__ == "__main__":
    unittest.main()
