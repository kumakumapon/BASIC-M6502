.include "basic.s"
.include "runtime.s"
.include "io.s"
.segment "HEADER"
.byte "NES", $1a, 2, 1, $10, $08, 0, 0, 7, 0, 0, 0, 0, $23
.segment "VECTORS"
.word nmi, reset, irq
.segment "CHR"
.incbin "font.chr"
.assert B_CHRGOT = B_CHRGET+6, error, "CHRGET opcode layout"
.assert B_TXTPTR = B_CHRGET+7, error, "CHRGET operand layout"
.assert B_RNDX+5 < $ff, error, "BASIC workspace overlaps FOUT buffer"
.assert B_BUF+B_BUFLEN <= $02f0, error, "Input buffer overflow"
.assert B_STKEND < B_BUF-4, error, "Stack overlaps input buffer sentinels"
