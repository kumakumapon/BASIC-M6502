# Microsoft BASIC 1.1 on NES

The build translates this repository's original Microsoft source; it does not
substitute another interpreter. The target is NTSC, NES 2.0, Mapper 1/MMC1,
32 KiB PRG-ROM, 8 KiB CHR-ROM and 8 KiB volatile PRG-RAM. Everything needed to
build and test is free software. The commercial Family BASIC ROM is not used.

## Windows quick start

Prerequisites: Python 3.10 or later, PowerShell, and Windows' `curl.exe`.
Python 3.12 was used for verification. Git is only needed to clone/update.

```powershell
./setup-tools.ps1 -Emulators -Tests
./build.ps1
./test.ps1 -Emulators
```

Downloads stay in `.tools/`, which is ignored by Git. `tools.lock.json` pins
versions and archive SHA256 hashes. The installer verifies every archive before
extracting. `-Emulators` adds Mesen CE 2.2.1 and FCEUX 2.6.6; `-Tests` installs
py65 1.2.0 into `.tools/python`. There are no machine-wide changes.

The cc65 Windows snapshot URL is a **rolling upstream download**. Its expected
hash is pinned, so a future replacement fails explicitly. Keep the verified
`.tools/cc65.zip` for offline reinstall, or build cc65 commit
`e11fb5c39371046ebe25485f984f644c5a0d65d3` from source. Updating the lock is a
deliberate toolchain upgrade requiring renewed build/tests, not a hash bypass.

To use an existing cc65 installation:

```powershell
./build.ps1 -Cc65Bin C:/cc65/bin
```

`build/` contains `basic.nes`, `basic.dbg`, `basic.map`, `basic.lst`, `basic.lbl`,
the generated `basic.s`, and the original font packed as `font.chr`.
`ca65 -g` and `ld65 --dbgfile` generate real debug information, distinct from
the VICE-format `.lbl` file. Keep `.dbg` beside the ROM when opening Mesen.

## Run and type

1. Start `.tools/Mesen_2.2.1_Windows/Mesen.exe` and open `build/basic.nes`.
2. In NES settings choose **Famicom**, region **NTSC**, and expansion device
   **Family BASIC Keyboard**. The ROM's NES 2.0 input-device field also allows
   Mesen to select the keyboard automatically.
3. Configure the emulated keyboard's key bindings to your PC keyboard. Enable
   keyboard input capture when needed so emulator shortcuts do not consume keys.
4. At `OK`, type `PRINT 1+2`, then Enter. The result is `3`.

For FCEUX, open the same ROM and select Family Keyboard as the expansion device
in input configuration. Bind the keyboard keys there; enable the emulator's
keyboard input mode when typing. The automated FCEUX test uses ASCII injection
instead of PC keyboard mappings (see validation below).

The layout follows the **emulated Japanese Family BASIC keyboard**, so PC key
labels need not match the characters produced. Letters are uppercase. Shift
selects the following symbols; bind the emulated key named in the left column:

| Emulated key | Normal | With Shift |
|---|---|---|
| 1, 2, 3, 4, 5 | `1 2 3 4 5` | `! " # $ %` |
| 6, 7, 8, 9 | `6 7 8 9` | `& ' ( )` |
| Semicolon | `;` | `+` |
| Colon | `:` | `*` |
| Minus | `-` | `=` |
| Comma, period, slash | `, . /` | `< > ?` |

Enter submits a line. **Del** erases the preceding character, including across
a wrapped screen row. Both Shift keys work. **Stop**, **Esc**, or **Ctrl+C**
interrupt execution; during line entry they discard the unfinished line.
Holding a character repeats after 25 frames, then every 4 frames. Kana, Grph,
function keys, cursor movement and Insert are not implemented. This is a line
editor: re-enter a numbered line to replace it, or enter just its number to delete.

```basic
10 FOR I=1 TO 5
20 PRINT I,I*I
30 NEXT I
LIST
RUN
20 PRINT "VALUE=";I
LIST
```

Supported interpreter features include floating point, integer/string arrays,
FOR/NEXT, GOSUB/RETURN, DATA/READ/RESTORE, INPUT, GET, string functions, and
the original mathematical functions. Errors use the original abbreviated names
(for example `SN`, `/0`, `OM`) followed by `ERROR`.

## Display and memory

| CPU range | Purpose |
|---|---|
| `$0000` through BASIC's `RNDX+4` | BASIC variables and executable CHRGET |
| `$00E0–$00E5` | Foreground, NMI and scrolling pointers |
| `$00FF–$010F` | Original floating-point output buffer |
| `$0110–$01FB` | CPU stack (including interrupt frames) |
| `$01FC–$01FF` | BASIC's original pre-input-buffer sentinel area, reserved above stack |
| `$0200–$02EF` | Line input buffer, maximum 239 characters plus terminator |
| `$0300–$0328` | Display and keyboard state |
| `$0400–$07BF` | 32 by 30 tile shadow screen |
| `$6000–$7FFF` | Programs, variables, arrays and strings, sharing 8 KiB |
| `$8000–$FFF9` | BASIC, RAM initialization image, platform code and constants |
| `$FFFA–$FFFF` | NMI, RESET and IRQ vectors |

The startup banner reports **8191 bytes free** before BASIC allocates its
end-of-program markers and variables. This is shared memory, not an 8191-byte
program-size guarantee. The linker map gives exact ROM addresses for each build.

Reset executes in MMC1's fixed last bank, initializes the mapper, disables APU
interrupts and rendering, waits for the PPU, initializes RAM and loads BASIC's
RAM template. BASIC then copies its ROM CHRGET implementation to executable
zero page. Assembly assertions protect its `+6`, `+7` instruction offsets and
the boundary between BASIC and platform RAM. The RAM ceiling is always `$8000`;
there is no RAM-size probing and no startup terminal-width question.

The screen uses an original 5x7 font in 8x8 tiles, with a steady underscore
cursor. The text viewport is 32 columns by 28 rows; the outer two rows stay
blank so the input cursor remains visible with normal NTSC overscan cropping.
CR moves to the next row, LF is ignored, and output wraps at 32 columns.
Scrolling shifts the shadow screen up one row. A bounded **single pending row
range** is the display queue: the producer waits while NMI owns that range,
then publishes the count last. This prevents overflow and partially modified
rows. NMI transfers at most three rows (96 tiles) per frame, saves A/X/Y and
does not enter BASIC or modify its workspace. A full scroll drains over ten
frames; visible redraw and modest output throughput are intentional tradeoffs
for simplicity and bounded VBlank work. Input is polled in the foreground.

## Saving, limitations and debugging

- Use emulator **save states** to preserve an entire running session. They are
  not BASIC SAVE/LOAD commands and are emulator/version-specific.
- SAVE/LOAD, battery-backed persistence, disk/tape access and PC-file access
  are not implemented. Power cycling starts an empty BASIC session.
- No PC text-paste service is exposed by the ROM. The Lua files are test
  fixtures, not a user-facing paste or file-transfer protocol.
- PEEK/POKE/WAIT/USR retain their low-level semantics. ROM and mapper/register
  addresses are real NES addresses, not Apple II or Family BASIC addresses.
  POKE can disrupt the interpreter or display; USR defaults to an error.
- NTSC only has been verified. No audio, graphics commands, gamepad text entry,
  PAL timing guarantees or physical-cartridge validation are claimed.
- During long output, execution interruption is checked at BASIC's statement
  boundaries. The renderer itself does not poll for Break.

The translator records `source:<line>` in generated assembly. Use it with the
listing and debugger to trace back to `m6502.asm`. It is intentionally scoped
to this dialect and this source, not a general MACRO-10 assembler. Notable
translation rules are six-character symbol significance, explicit/default
radices, immediate low-byte truncation, token high bits, RTS dispatch entries,
and forced absolute CHRGET loads. The neutral historical `REALIO=5` branch is
adapted with explicit NES input and fixed-memory initialization replacements.

## Automated validation

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/test_mesen.py
python scripts/test_fceux.py
```

Build first. `test.ps1 -Emulators` does all four steps. The emulator runners
write result files, transcripts and PNG screenshots to `build/` and fail if no
result is produced. They start fresh processes, never load save states, and
check the linked production ROM. For an external Mesen installation, pass its
executable path and enable Lua file I/O in that installation first. The runner
only adjusts the project-local portable Mesen configuration.

| Layer | What is exercised |
|---|---|
| Translation/ROM checks | Radix, character constants, symbol significance, deterministic generation, full math package, header, vectors, CHR data |
| py65 CPU integration | Reset, BASIC, modeled PPU transfers, keyboard matrix/repeat/modifiers, errors, GC, long input and wrapped deletion |
| Mesen CE 2.2.1 | Real NES CPU/PPU/MMC1 core, ROM scanner/editor/interpreter, 27 scripted cases, NMI timing and VBlank writes |
| FCEUX 2.6.6 | Independent NES CPU/PPU/MMC1 core, ROM editor/interpreter, the same 27 cases |

Mesen's keyboard class does not expose named buttons to Lua `setInput`, so the
Mesen fixture supplies electrical matrix values on `$4017`, interpreting the
ROM's `$4016` row/column commands. FCEUX injects ASCII at the keyboard-result
boundary, before the line editor. **These tests do not verify PC key bindings
or physical keyboard hardware.** The native keyboard matrix was cross-checked
against Mesen CE's implementation. Both emulators' generated screenshots were
visually inspected for legible text and final success messages.

The 27 emulator cases cover `PRINT 1+2`, strings, floating point, numbered-line
insertion/replacement/deletion, LIST/RUN, FOR/NEXT, GOSUB/RETURN, arrays,
division by zero, out of memory, string GC, overlong input, backspace, continuous
scrolling, BREAK and input after BREAK. Mesen measured a maximum **1,788 CPU
cycles** for NMI, below the approximately 2,273-cycle NTSC VBlank interval.
Additional CPU tests cover DATA/RESTORE, INPUT/GET, and math functions.

GitHub Actions builds on Windows and Linux. The Windows job also runs both NES
emulators and uploads ROM/debug files, transcripts and screenshots as artifacts.
The Linux job builds the exact cc65 source commit and runs the CPU suite.

## Linux / macOS build

With Python, Git, a C compiler and make installed:

```sh
git clone https://github.com/cc65/cc65.git .tools/cc65
git -C .tools/cc65 checkout e11fb5c39371046ebe25485f984f644c5a0d65d3
make -C .tools/cc65/src -j2 ca65 ld65
python3 -m pip install py65==1.2.0
python3 scripts/build.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The FCEUX launcher in this repository targets its Windows build. Native Linux
or macOS GUI configuration is not part of the Windows installation script.

## Sources and licenses

- [Original source](../m6502.asm) and [repository MIT license](../LICENSE).
- [cc65 installation](https://cc65.github.io/getting-started.html),
  [ca65](https://cc65.github.io/doc/ca65.html),
  [ld65](https://cc65.github.io/doc/ld65.html),
  [cc65 license](https://github.com/cc65/cc65/blob/e11fb5c39371046ebe25485f984f644c5a0d65d3/LICENSE).
- [Mesen CE 2.2.1](https://github.com/nesdev-org/MesenCE/releases/tag/2.2.1),
  [keyboard implementation](https://github.com/nesdev-org/MesenCE/blob/2.2.1/Core/NES/Input/FamilyBasicKeyboard.h),
  [Lua API](https://github.com/nesdev-org/MesenCE/blob/2.2.1/UI/Debugger/Documentation/LuaDocumentation.json).
- [FCEUX 2.6.6](https://github.com/TASEmulators/fceux/releases/tag/v2.6.6),
  [Lua implementation](https://github.com/TASEmulators/fceux/blob/v2.6.6/src/lua-engine.cpp).
- [NES 2.0](https://www.nesdev.org/wiki/NES_2.0),
  [MMC1](https://www.nesdev.org/wiki/MMC1),
  [PPU reference](https://www.nesdev.org/wiki/PPU_programmer_reference).

Mesen CE and FCEUX are GPL software; cc65 has its own permissive license; py65
is BSD licensed. Downloaded tools retain their own licenses and are not checked
into this repository. The translation, runtime, font and test code are covered
by this repository's MIT license.
