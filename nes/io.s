; Keyboard scanning follows Mesen CE FamilyBasicKeyboard.h: active-low D1-D4,
; column on D1, row reset on D0, enabled by D2; falling column advances row.
matrix = $0310                 ; 18 nibbles (9 rows x 2 columns)
key_frame = $0322
previous_key = $0323
repeat_delay = $0324
shifted = $0325
key_bits = $0326
key_value = $0327
input_length = $0328

.segment "CODE"
key_poll:
    lda frame
    cmp key_frame
    bne @scan
    lda #0
    rts
@scan:
    sta key_frame
    lda #5
    sta $4016
    ldx #0
@half:
    lda $4017
    lsr a
    eor #$0f
    and #$0f
    sta matrix,x
    inx
    lda #6
    sta $4016
    lda $4017
    lsr a
    eor #$0f
    and #$0f
    sta matrix,x
    inx
    lda #4
    sta $4016
    cpx #18
    bne @half
    lda matrix+1
    and #2
    sta shifted
    lda matrix+15
    and #1
    ora shifted
    sta shifted
    ldx #0
    ldy #0
@nibble:
    lda matrix,x
    sta key_bits
@bit:
    lsr key_bits
    bcc @skip
    lda shifted
    beq @plain
    lda shifted_keys,y
    jmp @key
@plain:
    lda plain_keys,y
@key:
    beq @skip
    cmp #'C'
    bne @found
    lda matrix+14
    and #8
    beq @letter_c
    lda #3
    bne @found
@letter_c:
    lda #'C'
    bne @found
@skip:
    iny
    tya
    and #3
    bne @bit
    inx
    cpx #18
    bne @nibble
    lda #0
@found:
    cmp previous_key
    beq @held
    sta previous_key
    ldx #25
    stx repeat_delay
    rts
@held:
    cmp #0
    beq @return
    dec repeat_delay
    beq @repeat
    lda #0
@return:
    rts
@repeat:
    ldx #4
    stx repeat_delay
    rts

B_CZGETL:
    txa
    pha
    tya
    pha
    jsr key_poll
    sta key_value
    pla
    tay
    pla
    tax
    lda key_value
    rts

B_INCHR:
    jsr B_CZGETL
    cmp #0
    beq B_INCHR
    rts

B_ISCNTC:
    php
    pha
    jsr B_CZGETL
    cmp #3
    beq @break
    pla
    plp
    rts
@break:
    pla
    plp
    lda #3
    cmp #3
    jmp B_STOP

B_INLIN:
    lda #0
    sta input_length
@read:
    jsr B_INCHR
    cmp #3
    beq @cancel
    cmp #13
    beq @done
    cmp #8
    beq @delete
    cmp #32
    bcc @read
    ldx input_length
    cpx #B_BUFLEN-1
    bcs @read
    sta B_BUF,x
    inc input_length
    jsr B_OUTDO
    jmp @read
@delete:
    ldx input_length
    beq @read
    dec input_length
    jsr B_OUTCH
    lda col
    sta B_TRMPOS
    jmp @read
@cancel:
    lda #0
    sta input_length
@done:
    ldx input_length
    lda #0
    sta B_BUF,x
    jsr B_CRDO
    ldx #<(B_BUF-1)
    ldy #>(B_BUF-1)
    lda #0
    rts

.segment "RODATA"
plain_keys:
.byte 0,13,'[',']', 0,0,92,3
.byte 0,'@',':',';', '_','/','-','^'
.byte 0,'O','L','K', '.',',','P','0'
.byte 0,'I','U','J', 'M','N','9','8'
.byte 0,'Y','G','H', 'B','V','7','6'
.byte 0,'T','R','D', 'F','C','5','4'
.byte 0,'W','S','A', 'X','Z','E','3'
.byte 0,3,'Q',0, 0,0,'1','2'
.byte 0,0,0,0, 0,' ',8,0
shifted_keys:
.byte 0,13,'[',']', 0,0,92,3
.byte 0,'@','*','+', '_','?','=','^'
.byte 0,'O','L','K', '>','<','P','0'
.byte 0,'I','U','J', 'M','N',')','('
.byte 0,'Y','G','H', 'B','V',39,'&'
.byte 0,'T','R','D', 'F','C','%','$'
.byte 0,'W','S','A', 'X','Z','E','#'
.byte 0,3,'Q',0, 0,0,'!',34
.byte 0,0,0,0, 0,' ',8,0
