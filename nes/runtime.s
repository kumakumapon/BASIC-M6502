; BASIC owns $0000 through B_RNDX+4 and $00ff-$010f.
; Runtime zero page is separate; NMI never touches foreground pointers.
ptr = $e0
nmi_ptr = $e2
copy_ptr = $e4
.assert B_RNDX+5 <= ptr, error, "NES/BASIC zero page overlap"
screen = $0400                 ; 960 bytes, through $07bf
FIRST_ROW = 1                  ; keep both edge rows outside the text viewport
ROW_LIMIT = 29                 ; default NTSC overscan hides rows 0 and 29
row = $0300
col = $0301
pending = $0302                ; published last, zero means foreground owns screen
transfer_row = $0303
frame = $0304
saved_char = $0305
first_row = $0306
row_budget = $0307             ; NMI only
scrolling = $0308
last_row = $0309

.segment "CODE"
reset:
    sei
    cld
    ldx #$ff
    txs
    inx
    stx $2000
    stx $2001
    stx $4010
    stx $4015
    lda #$40
    sta $4017
    ; Execute reset in the fixed last 16 KiB bank before configuring MMC1.
    lda #$80
    sta $8000
    lda #$0e                   ; vertical mirroring, fixed last bank, 8 KiB CHR
    jsr mmc_control
    lda #0
    sta $a000
    sta $a000
    sta $a000
    sta $a000
    sta $a000
    sta $e000                  ; first bank at $8000; PRG-RAM enabled
    sta $e000
    sta $e000
    sta $e000
    sta $e000
    bit $2002
@v1: bit $2002
    bpl @v1
@v2: bit $2002
    bpl @v2
    lda #0
    tax
@clear:
    sta $0000,x
    sta $0200,x
    sta $0300,x
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    inx
    bne @clear
    ; Initialize the entire interpreter's RAM template, including initial data.
    .import __ZPINIT_LOAD__, __ZPINIT_SIZE__
@zp: lda __ZPINIT_LOAD__,x
    sta $0000,x
    inx
    bne @zp
    ldx #<(__ZPINIT_SIZE__-$100-1)
@fp: lda __ZPINIT_LOAD__+$100,x
    sta $0100,x
    dex
    bpl @fp
    lda #$20
    sta $2006
    lda #0
    sta $2006
    ldy #4
    ldx #0
@nt: sta $2007
    inx
    bne @nt
    dey
    bne @nt
    lda #$3f
    sta $2006
    lda #0
    sta $2006
    ldx #0
@pal: lda palette,x
    sta $2007
    inx
    cpx #32
    bne @pal
    lda #0
    sta $2005
    sta $2005
    lda #$80
    sta $2000
    lda #$0a
    sta $2001
    lda #FIRST_ROW
    sta row
    jmp B_INIT

mmc_control:
    sta $8000
    lsr a
    sta $8000
    lsr a
    sta $8000
    lsr a
    sta $8000
    lsr a
    sta $8000
    rts

nmi:
    pha
    txa
    pha
    tya
    pha
    inc frame
    lda #3                     ; <=96 tiles/frame, safely within NTSC VBlank
    sta row_budget
    bit $2002
@next:
    lda pending
    beq @done
    ldx transfer_row
    lda row_low,x
    sta nmi_ptr
    lda row_high,x
    sta nmi_ptr+1
    clc
    adc #$1c                   ; $0400 shadow -> $2000 nametable
    sta $2006
    lda nmi_ptr
    sta $2006
    ldy #0
@tile:
    lda (nmi_ptr),y
    sta $2007
    iny
    cpy #32
    bne @tile
    inc transfer_row
    dec pending
    dec row_budget
    bne @next
@done:
    lda #0
    sta $2005
    sta $2005
    pla
    tay
    pla
    tax
    pla
irq:
    rti

console_wait:
    lda pending
    bne console_wait
    rts

set_ptr:
    ldx row
    lda row_low,x
    sta ptr
    lda row_high,x
    sta ptr+1
    ldy col
    rts

B_OUTCH:
    pha
    txa
    pha
    tya
    pha
    tsx
    lda $0103,x
    and #$7f                   ; historical DC strings mark their final byte
    sta saved_char
    jsr console_wait
    lda #0
    sta scrolling
    lda row
    sta first_row
    sta last_row
    jsr set_ptr
    cpy #32
    beq @no_cursor
    lda #32
    sta (ptr),y
@no_cursor:
    lda saved_char
    cmp #13
    beq @newline
    cmp #8
    beq @delete
    cmp #32
    bcc @cursor
    cmp #127
    bcs @cursor
    ldy col
    cpy #32
    bne @put
    jsr newline
@put:
    jsr set_ptr
    lda saved_char
    sta (ptr),y
    inc col
    bne @cursor
@newline:
    jsr newline
    jmp @cursor
@delete:
    lda col
    bne @back
    lda row
    cmp #FIRST_ROW
    beq @cursor
    dec row
    lda row
    sta first_row
    lda #32
    sta col
@back:
    dec col
@cursor:
    jsr set_ptr
    cpy #32
    beq @publish
    lda #127
    sta (ptr),y
@publish:
    lda row
    cmp last_row
    bcc :+
    sta last_row
:
    lda scrolling
    beq @partial
    lda #FIRST_ROW
    sta transfer_row
    lda #ROW_LIMIT-FIRST_ROW
    bne @commit
@partial:
    lda first_row
    sta transfer_row
    lda last_row
    sec
    sbc first_row
    clc
    adc #1
@commit:
    sta pending                ; atomic ownership handoff to NMI
    pla
    tay
    pla
    tax
    pla
    rts

newline:
    lda #0
    sta col
    inc row
    lda row
    cmp #ROW_LIMIT
    bcc @done
    dec row
    inc scrolling
    lda #<(screen+32*FIRST_ROW)
    sta ptr
    lda #>(screen+32*FIRST_ROW)
    sta ptr+1
    lda #<(screen+32*(FIRST_ROW+1))
    sta copy_ptr
    lda #>(screen+32*(FIRST_ROW+1))
    sta copy_ptr+1
    ldx #ROW_LIMIT-FIRST_ROW-1
@row:
    ldy #0
@copy:
    lda (copy_ptr),y
    sta (ptr),y
    iny
    cpy #32
    bne @copy
    clc
    lda copy_ptr
    sta ptr
    adc #32
    sta copy_ptr
    lda copy_ptr+1
    sta ptr+1
    adc #0
    sta copy_ptr+1
    dex
    bne @row
    lda #32
    ldy #31
@blank:
    sta (ptr),y
    dey
    bpl @blank
@done:
    rts

.segment "RODATA"
palette:
.repeat 8
    .byte $0f,$30,$30,$30
.endrepeat
row_low:
.repeat 30,I
    .byte <(screen+32*I)
.endrepeat
row_high:
.repeat 30,I
    .byte >(screen+32*I)
.endrepeat
