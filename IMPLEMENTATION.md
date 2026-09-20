# Issue #1: NES port checkpoint

This file is the durable handoff for the NES port. Original source: `m6502.asm`.
No implementation had started when the draft PR was opened.

## Intended scope

Build the repository's Microsoft BASIC with ca65/ld65 for NTSC NES,
NES 2.0 MMC1, 32 KiB PRG-ROM, 8 KiB PRG-RAM and 8 KiB CHR-ROM.
Provide startup, text console, Family BASIC Keyboard input, and reproducible
Windows tooling. SAVE/LOAD persistence is deferred; use emulator save states.

## Checkpoints

- [x] Open draft PR before implementation: https://github.com/kumakumapon/BASIC-M6502/pull/2
- [ ] Pin tool downloads and record versions/hashes.
- [ ] Convert original assembly and validate layout and RAM initialization.
- [ ] Implement NES startup, display, keyboard and interpreter integration.
- [x] Build ROM, map, listing and debug symbols.
- [ ] Test arithmetic, editing, control flow, arrays, strings and error paths.
- [ ] Test display, interruption, cold boot and two NES emulators where available.
- [ ] Document installation, controls, limitations and validation evidence.
- [ ] Update PR and mark ready when implementation and verification are complete.

## Resume

Read this file, the PR description, and `git status`. Continue from the first
unchecked checkpoint. Record exact commands, test results and remaining issues
here before pushing each milestone. Do not mark unexecuted checks as passed.

## Decisions and evidence

- Starting commit: `7460af2c03ae19c0e60ff327489229d2005b9357`.
- No repository AGENTS.md or existing build system was found.
- Python 3.12 and CMake are available; ca65/ld65 are not on PATH.
- Preserve the historical source; generate a separate ca65 translation.

## Checkpoint 2026-09-20: first working ROM

- `python scripts/build.py` builds `build/basic.nes`, `.map`, `.lst`, `.dbg`, `.lbl`.
- `python tests/test_runtime.py`: 7 CPU integration tests passed (48 seconds).
  Covers cold boot, arithmetic, strings, edits, loops, subroutines, arrays,
  division/syntax/out-of-memory errors, repeated string allocation/GC,
  overlong input, deletion, BREAK, keyboard modifiers/repeat and PPU row transfers.
- BASIC occupies $8000-$9fb4; initialized RAM image $9fb5-$a0c4;
  platform code starts $c000. NMI transfers at most 96 tiles/frame.
- These tests use py65 with modeled I/O, **not** a complete NES PPU emulator.
  Mesen CE and independent NES emulator validation remain next.
- Local tools: `.tools/cc65/bin` (V2.19 Git e11fb5c),
  `.tools/Mesen_2.2.1_Windows/Mesen.exe`, `.tools/python` (py65 1.2.0).
- cc65 archive SHA256: `4994453cc76987bbf3c3dda77e8497bab369c7348f05d88871af9f2dd491fffd`.
- Mesen archive SHA256: `c19e10b3b3865eb0e86e4d01bf09a5027a4452081c04b5bd5b6cbbf76e346fd6`.
- Mesen's 2.2.1 keyboard does not expose named buttons to Lua setInput;
  automated NES tests should inject matrix readings at $4017 and validate
  ROM-side $4016 scanning, with this limitation stated explicitly.
