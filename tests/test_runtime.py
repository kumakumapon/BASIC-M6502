"""CPU-level integration tests of the linked ROM; not a substitute for PPU QA."""

from pathlib import Path
from collections import deque
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".tools/python"))
from py65.devices.mpu6502 import MPU


def symbols():
    result = {}
    for line in (ROOT / "build/basic.lbl").read_text().splitlines():
        _, address, name = line.split()
        result[name.lstrip(".")] = int(address, 16)
    return result


class Bus:
    def __init__(self):
        self.ram = bytearray(65536)
        rom = (ROOT / "build/basic.nes").read_bytes()
        self.ram[0x8000:] = rom[16:32784]
        self.ppu = bytearray(0x4000)
        self.ppu_address = 0
        self.latch = False
        self.control = 0
        self.keyboard_row = 0
        self.column = 0
        self.enabled = False
        self.keys = set()
        self.bad_writes = []
        self.ppu_writes = []

    def __getitem__(self, a):
        if isinstance(a, slice):
            return self.ram[a]
        a &= 65535
        if a < 0x2000:
            return self.ram[a & 0x7FF]
        if a == 0x2002:
            self.latch = False
            return 0x80
        if a == 0x4017:
            bits = sum(
                1 << i
                for i in range(4)
                if self.keyboard_row * 8 + self.column * 4 + i in self.keys
            )
            return ((~bits) << 1) & 0x1E if self.enabled else 0
        return self.ram[a]

    def __setitem__(self, a, v):
        a &= 65535
        v &= 255
        if a < 0x2000:
            self.ram[a & 0x7FF] = v
        elif a == 0x2000:
            self.control = v
        elif a == 0x2006:
            self.ppu_address = (
                ((self.ppu_address & 255) | (v << 8))
                if not self.latch
                else ((self.ppu_address & 0xFF00) | v)
            )
            self.latch = not self.latch
        elif a == 0x2007:
            self.ppu[self.ppu_address & 0x3FFF] = v
            self.ppu_writes.append(self.ppu_address & 0x3FFF)
            self.ppu_address += 32 if self.control & 4 else 1
        elif a == 0x2005:
            self.latch = not self.latch
        elif a == 0x4016:
            col = (v >> 1) & 1
            if not col and self.column:
                self.keyboard_row = (self.keyboard_row + 1) % 10
            if v & 1:
                self.keyboard_row = 0
            self.column = col
            self.enabled = bool(v & 4)
        elif 0x6000 <= a < 0x8000:
            self.ram[a] = v
        elif a in (0x8000, 0xA000, 0xE000):
            pass
        elif a in (0x2001, 0x4010, 0x4015, 0x4017):
            pass
        else:
            self.bad_writes.append((a, v))


class Machine:
    def __init__(self):
        self.labels = symbols()
        self.bus = Bus()
        self.cpu = MPU(memory=self.bus, pc=None)
        self.inputs = deque()
        self.output = []
        self.next_nmi = 29780
        self.nmi_start = None
        self.max_nmi = 0
        self.break_requested = False

    def step(self):
        c = self.cpu
        if c.processorCycles >= self.next_nmi:
            self.next_nmi += 29780
            if self.bus.control & 128 and self.nmi_start is None:
                self.nmi_start = c.processorCycles
                c.nmi()
        if c.pc == self.labels["B_OUTCH"]:
            self.output.append(chr(c.a & 127))
        if self.break_requested and c.pc == self.labels["B_ISCNTC"]:
            self.bus.keys = {7}
        op = self.bus[c.pc]
        c.step()
        if op == 0x40 and self.nmi_start is not None:
            self.max_nmi = max(self.max_nmi, c.processorCycles - self.nmi_start)
            self.nmi_start = None

    def run(self, text="", limit=8_000_000):
        self.inputs.extend(text.encode("ascii"))
        start = len(self.output)
        for _ in range(limit):
            if self.cpu.pc == self.labels["B_INCHR"]:
                if not self.inputs:
                    return "".join(self.output[start:])
                self.cpu.a = self.inputs.popleft()
                self.cpu.p = (
                    (self.cpu.p & ~0x82)
                    | (0x02 if self.cpu.a == 0 else 0)
                    | (self.cpu.a & 128)
                )
                self.cpu.pc = self.cpu.stPopWord() + 1
            self.step()
        raise AssertionError(
            f'Timeout at {self.cpu.pc:04x}: {"".join(self.output[-200:])!r}'
        )

    def call(self, label):
        self.cpu.stPushWord(0x5FFF)
        self.cpu.pc = self.labels[label]
        for _ in range(100000):
            if self.cpu.pc == 0x6000:
                return self.cpu.a
            self.step()
        raise AssertionError("Subroutine timeout: " + label)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.m = Machine()
        self.boot = self.m.run()

    def command(self, text):
        return self.m.run(text + "\r")

    def test_cold_boot_and_layout(self):
        self.assertIn("8191 BYTES FREE", self.boot)
        self.assertIn("NES BASIC V1.1", self.boot)
        self.assertIn("OK", self.boot)
        self.assertFalse(self.m.bus.bad_writes)
        self.assertLess(self.m.labels["B_RNDX"] + 5, 0xE0)
        self.assertEqual(self.m.bus.ram[0x1FC:0x1FE], b"\x01\x01")

    def test_arithmetic_and_strings(self):
        for cmd, want in [
            ("PRINT 1+2", " 3 "),
            ('PRINT "HELLO"', "HELLO"),
            ("PRINT 1.5*2.5", " 3.75 "),
            ("PRINT 2^8", " 256 "),
            ("PRINT SQR(81)", " 9 "),
            ('PRINT LEN("ABCDE")', " 5 "),
            ("PRINT INT(-1.5)", "-2 "),
            ("PRINT ABS(-7)", " 7 "),
            ("PRINT SIN(0);COS(0);ATN(0)", " 0  1  0 "),
            ('PRINT MID$("ABCDE",2,3)', "BCD"),
            ('PRINT LEFT$("ABCDE",2)+RIGHT$("ABCDE",2)', "ABDE"),
        ]:
            with self.subTest(cmd=cmd):
                self.assertIn(want, self.command(cmd))

    def test_data_restore_input_and_get(self):
        self.command('10 DATA 12,"DATA OK":READ A,B$:PRINT A;B$:RESTORE:READ C:PRINT C')
        self.assertIn(" 12 DATA OK", self.command("RUN"))
        self.command("NEW")
        self.command("10 INPUT A")
        self.command("20 GET B$:PRINT LEN(B$):PRINT A")
        output = self.m.run("RUN\r6\r")
        self.assertIn(" 6 ", output)
        self.assertIn(" 0 ", output)

    def test_delete_across_wrapped_row(self):
        # Deleting across the boundary must flush both the old and new rows.
        self.m.run("REM " + ("X" * 29) + "\b\b")
        self.m.call("console_wait")
        self.assertEqual(self.m.bus.ppu[0x2000:0x23C0], self.m.bus.ram[0x400:0x7C0])

    def test_program_editing_control_and_arrays(self):
        for line in [
            "10 DIM A(3):S=0",
            "20 FOR I=1 TO 3:A(I)=I*2:S=S+A(I):NEXT I",
            "30 GOSUB 100:PRINT S:END",
            "100 S=S+1:RETURN",
        ]:
            self.command(line)
        self.assertIn(" 13 ", self.command("RUN"))
        self.command("100 S=S+2:RETURN")
        self.assertIn(" 14 ", self.command("RUN"))
        self.assertIn("100 S=S+2:RETURN", self.command("LIST"))
        self.command("100")
        self.assertNotIn("100 S=", self.command("LIST"))
        self.command("NEW")
        self.assertNotIn("10 DIM", self.command("LIST"))

    def test_errors_and_gc(self):
        self.assertIn("/0 ERROR", self.command("PRINT 1/0"))
        self.assertIn("SN ERROR", self.command("PRINT )"))
        self.assertIn("OM ERROR", self.command("DIM A(10000)"))
        self.command("NEW")
        self.command('10 A$="":FOR I=1 TO 500:A$=RIGHT$(A$+"1234567890",100):NEXT I')
        self.command('20 PRINT LEN(A$):PRINT "GC OK"')
        out = self.command("RUN")
        self.assertIn(" 100 ", out)
        self.assertIn("GC OK", out)

    def test_input_delete_long_line_and_break(self):
        self.assertIn(" 3 ", self.command("PRINT 1+9\b2"))
        self.command("REM " + ("X" * 300))
        self.assertIn(" 7 ", self.command("PRINT 7"))
        self.command("10 GOTO 10")
        self.m.break_requested = True
        self.assertIn("BREAK", self.command("RUN"))
        self.m.break_requested = False
        self.m.bus.keys = set()
        self.assertIn(" 8 ", self.command("PRINT 8"))

    def test_keyboard_shift_delete_repeat(self):
        def poll(keys):
            self.m.bus.keys = set(keys)
            self.m.bus.ram[0x304] = (self.m.bus.ram[0x304] + 1) & 255
            return self.m.call("B_CZGETL")

        self.assertEqual(poll([49]), ord("W"))
        self.assertEqual(poll([49]), 0)
        for _ in range(24):
            result = poll([49])
        self.assertEqual(result, ord("W"))
        self.assertEqual(poll([]), 0)
        self.assertEqual(poll([63, 60]), ord('"'))
        self.assertEqual(poll([70]), 8)
        self.assertEqual(poll([45, 59]), 3)

    def test_scrolling_nmi_and_ppu(self):
        self.command("FOR I=1 TO 40:PRINT I:NEXT I")
        self.m.call("console_wait")
        self.assertLess(self.m.max_nmi, 2273)
        self.assertEqual(self.m.bus.ppu[0x2000:0x23C0], self.m.bus.ram[0x400:0x7C0])
        self.assertFalse(self.m.bus.bad_writes)
        self.assertEqual(self.m.bus.ram[0x300], 28)
        self.assertEqual(self.m.bus.ppu[0x2000:0x2020], bytes(32))
        self.assertEqual(self.m.bus.ppu[0x23A0:0x23C0], bytes(32))
        cursor = 0x2000 + 28 * 32 + self.m.bus.ram[0x301]
        self.assertEqual(self.m.bus.ppu[cursor], 127)


if __name__ == "__main__":
    unittest.main(verbosity=2)
