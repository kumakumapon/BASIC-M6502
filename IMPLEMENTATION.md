# Issue #1: NES port checkpoint

This file is the durable handoff for the NES port. Original source: `m6502.asm`.
No implementation had started when the draft PR was opened.

## Intended scope

Build the repository's Microsoft BASIC with ca65/ld65 for NTSC NES,
NES 2.0 MMC1, 32 KiB PRG-ROM, 8 KiB PRG-RAM and 8 KiB CHR-ROM.
Provide startup, text console, Family BASIC Keyboard input, and reproducible
Windows tooling. SAVE/LOAD persistence is deferred; use emulator save states.

## Checkpoints

- [ ] Open draft PR before implementation.
- [ ] Pin tool downloads and record versions/hashes.
- [ ] Convert original assembly and validate layout and RAM initialization.
- [ ] Implement NES startup, display, keyboard and interpreter integration.
- [ ] Build ROM, map, listing and debug symbols.
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
