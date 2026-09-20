"""Translate the checked-in MACRO-10 source into ca65 syntax for the NES port.

The restricted translator deliberately fails on unknown statements. The original
source is never rewritten. Source line numbers accompany generated statements.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


class Converter:
    def __init__(self):
        self.symbols = {"BUF": 512}
        self.radix = 10
        self.out = [
            "; Generated from m6502.asm by scripts/convert.py",
            '.setcpu "6502"',
        ]
        self.overrides = dict(
            REALIO=5,
            BUFPAG=2,
            BUF=512,
            LINLEN=32,
            BUFLEN=240,
            ROMLOC=32768,
            RAMLOC=24576,
            NULCMD=0,
            GETCMD=1,
            DISKO=0,
            LONGI=0,
            STKEND=507,
        )
        self.serial = 0

    def expr(self, s):
        s = s.strip().upper()
        s = re.sub(r'"(.)"', lambda m: "^D" + str(ord(m[1])), s)
        # Convert explicit radix first, protecting results from default radix.
        nums = []

        def number(m):
            nums.append(str(int(m[2], 8 if m[1] == "O" else 10)))
            return f"@{len(nums)-1}@"

        s = re.sub(r"\^([OD])([0-9]+)", number, s)

        # MACRO-10 accepts 8/9 even under RADIX 8 (e.g. 8*ADDPRC+230).
        def default_number(m):
            n = 0
            for digit in m[0]:
                n = n * self.radix + int(digit)
            return str(n)

        s = re.sub(r"(?<![\w@])\d+(?![\w@])", default_number, s)
        s = re.sub(r"@(\d+)@", lambda m: nums[int(m[1])], s)
        s = s.replace("<", "(").replace(">", ")").replace("!", "|")
        s = s.replace(".", "*")
        # ca65 reserves register A and several instruction names as symbols.
        return re.sub(r"\b([A-Z][A-Z0-9]*)\b", lambda m: "B_" + m[0][:6], s)

    def value(self, s):
        s = self.expr(s)
        s = re.sub(r"B_([A-Z][A-Z0-9]*)", lambda m: str(self.symbols[m[1]]), s)
        if not re.fullmatch(r"[\d\s()+*/|&-]+", s):
            raise ValueError(f"Cannot evaluate {s}")
        return int(eval(s.replace("/", "//"), {"__builtins__": {}}, {}))

    def emit(self, s, line):
        self.out.append(f"{s} ; source:{line}")

    def statement(self, s, line):
        s = s.strip()
        if not s:
            return
        label = re.match(r"([\w$]+)::?\s*", s)
        if label:
            name = label[1].upper()[:6]
            if name != "$Z":
                self.emit("B_" + name + ":", line)
            s = s[label.end() :].strip()
            if not s:
                return
        if re.match(
            r"^(TITLE|SEARCH|SALL|SUBTTL|PAGE|PRINTX|PURGE|END|XLIST|LIST|\.XCREF|\.CREF)\b",
            s,
            re.I,
        ):
            return
        if s.upper().startswith("RADIX"):
            self.radix = int(s.split()[1])
            return
        assignment = re.match(r"(\w+)\s*==?\s*(.*)", s)
        if assignment:
            name, expr = assignment[1].upper()[:6], assignment[2]
            if name in self.overrides:
                expr = "^D" + str(self.overrides[name])
            try:
                self.symbols[name] = self.value(expr)
                result = str(self.symbols[name])
            except KeyError:
                result = self.expr(expr)
                self.emit(f"B_{name} = {result}", line)
                return
            self.emit(f"B_{name} .set {result}", line)
            return
        if s.upper().startswith("ORG"):
            arg = s.split()[1].upper()
            if arg == "0":
                self.emit('.segment "ZPINIT": zeropage\n.org 0\nB_BUF = $0200', line)
            elif arg == "255":
                self.emit('.assert * <= $ff, error, "BASIC zero page overflow"', line)
                self.emit(".res $ff-*, 0", line)
            elif arg == "ROMLOC":
                self.emit('.reloc\n.segment "BASIC"', line)
            else:
                raise ValueError(s)
            return
        string = re.fullmatch(r'(DCI|DCE|DC|DT)\s*"(.*)"', s, re.I)
        if string:
            op, value = string[1].upper(), string[2]
            data = list(value.encode("ascii"))
            if op in ("DCI", "DCE", "DC"):
                data[-1] |= 128
            if op in ("DCI", "DCE"):
                self.symbols["Q"] += 1 if op == "DCI" else 2
                self.emit(f'B_Q .set {self.symbols["Q"]}', line)
            self.emit(".byte " + ",".join(map(str, data)), line)
            return
        adr = re.fullmatch(r"ADR\s*\((.*)\)", s, re.I)
        if adr:
            self.emit(".word " + self.expr(adr[1]), line)
            return
        parts = s.split(None, 1)
        op, arg = parts[0].upper(), parts[1].strip() if len(parts) > 1 else ""
        arg = arg.rstrip(",")
        if op == "BLOCK":
            self.emit(".res " + self.expr(arg) + ", 0", line)
        elif op == "EXP":
            self.emit(".byte " + self.expr(arg), line)
        elif op == "XWD":
            self.emit(".byte " + self.expr(arg.split(",")[1]), line)
        elif op in ("ACRLF", "SKIP1", "SKIP2"):
            self.emit(
                ".byte " + dict(ACRLF="13,10", SKIP1="$24", SKIP2="$2c")[op], line
            )
        elif op == "SYNCHK":
            self.emit("lda #<(" + self.expr(arg) + ")\njsr B_SYNCHR", line)
        elif op in ("JEQ", "JNE"):
            self.serial += 1
            self.emit(
                f'{"bne" if op=="JEQ" else "beq"} cv_{self.serial}\njmp {self.expr(arg)}\ncv_{self.serial}:',
                line,
            )
        elif op == "INCW":
            self.serial += 1
            a = self.expr(arg)
            self.emit(
                f"inc {a}\nbne cv_{self.serial}\ninc {a}+1\ncv_{self.serial}:", line
            )
        elif op in ("CLR", "COM"):
            a = self.expr(arg)
            self.emit(
                ("lda #0" if op == "CLR" else f"lda {a}\neor #255") + f"\nsta {a}", line
            )
        elif op in (
            "LDWD",
            "LDWDI",
            "LDWX",
            "LDWXI",
            "LDXY",
            "LDXYI",
            "STWD",
            "STWX",
            "STXY",
            "PULWD",
            "PSHWD",
        ):
            a = self.expr(arg)
            if op == "PULWD":
                code = f"pla\nsta {a}\npla\nsta {a}+1"
            elif op == "PSHWD":
                code = f"lda {a}+1\npha\nlda {a}\npha"
            else:
                pair = (
                    ("a", "y")
                    if "WD" in op
                    else (("a", "x") if "WX" in op else ("x", "y"))
                )
                ins = "ld" if op.startswith("LD") else "st"
                args = (f"#<({a})", f"#>({a})") if op.endswith("I") else (a, a + "+1")
                code = "\n".join(ins + r + " " + v for r, v in zip(pair, args))
            self.emit(code, line)
        elif op in ("BCCA", "BCSA", "BEQA", "BNEA", "BMIA", "BPLA", "BVCA", "BVSA"):
            self.emit(op[:3].lower() + " " + self.expr(arg), line)
        elif re.fullmatch(r"(LDA|LDX|LDY|ADC|SBC|CMP|CPX|CPY|AND|ORA|EOR)I", op):
            self.emit(op[:3].lower() + " #<(" + self.expr(arg) + ")", line)
        elif re.fullmatch(r"(LDA|STA|ADC|SBC|CMP|AND|ORA|EOR)D[XY]", op):
            self.emit(
                op[:3].lower()
                + " ("
                + self.expr(arg)
                + ("),y" if op[-1] == "Y" else ",x)"),
                line,
            )
        elif op == "JMPD":
            self.emit("jmp (" + self.expr(arg) + ")", line)
        elif (
            op
            in "LDA LDX LDY STA STX STY ADC SBC CMP CPX CPY AND ORA EOR BIT INC DEC ASL LSR ROL ROR JMP JSR BCC BCS BEQ BNE BMI BPL BVC BVS PHA PHP PLA PLP TAX TAY TSX TXA TXS TYA INX INY DEX DEY RTS RTI CLC SEC CLI SEI CLD SED CLV NOP BRK".split()
        ):
            a = self.expr(arg)
            a = re.sub(r",B_([XY])$", lambda m: "," + m[1].lower(), a)
            if a == "B_A":
                a = "a"
            self.emit(op.lower() + " " + a, line)
        else:
            if re.fullmatch(r"[A-Z][A-Z0-9]*", s):
                self.emit(".byte " + self.expr(s), line)
                return
            try:
                self.value(s)
            except (KeyError, ValueError, SyntaxError):
                raise ValueError(f"Unsupported at {line}: {s}")
            self.emit(".byte " + self.expr(s), line)

    def run(self, text):
        # Remove COMMENT blocks and semicolon comments before parsing brackets.
        lines = text.replace("\f", "").split("\n")
        clean = []
        comment = False
        for line in lines:
            if line.startswith("COMMENT "):
                comment = line.split()[1]
                clean.append("")
                continue
            if comment:
                if line.strip() == comment:
                    comment = False
                clean.append("")
                continue
            # Semicolons inside quoted strings are data; comments may contain quotes.
            quoted = False
            for i, ch in enumerate(line):
                if ch == '"':
                    quoted = not quoted
                if ch == ";" and not quoted:
                    line = line[:i]
                    break
            clean.append(line)
        # DT's IRPC syntax contains an unmatched quote as a macro parameter.
        # Its semantics are implemented explicitly above, as are all DEFINEs.
        for i, line in enumerate(clean):
            if re.match(r"DEFINE\s+DT\(Q\),<", line):
                if not clean[i + 1].startswith("IRPC"):
                    raise ValueError("Unexpected DT macro definition")
                clean[i : i + 2] = ["", ""]
                break
        else:
            raise ValueError("Expected DT macro definition was not found")
        src = "\n".join(clean)

        def block(pos, active=True, end=False):
            while pos < len(src):
                while pos < len(src) and src[pos].isspace():
                    pos += 1
                if pos == len(src):
                    break
                if src[pos] == ">":
                    if not end:
                        raise ValueError(f"Unexpected > at {pos}")
                    return pos + 1
                line = src.count("\n", 0, pos) + 1
                # A label may precede a conditional.
                lm = re.match(r"([\w$]+)::?\s*", src[pos:])
                if lm:
                    if active:
                        self.statement(lm[0], line)
                    pos += lm.end()
                    continue
                directive = re.match(
                    r"(IFE|IFN|IF1|IF2|IFNDEF|REPEAT|DEFINE)\b", src[pos:], re.I
                )
                if directive:
                    op = directive[1].upper()
                    comma = src.index(",", pos)
                    opening = src.index("<", comma)
                    head = src[pos + directive.end() : comma].strip()
                    if op == "DEFINE":
                        pos = block(opening + 1, False, True)
                        continue
                    condition = False
                    count = 1
                    if active:
                        if op in ("IF1", "IF2", "IFNDEF"):
                            condition = False
                        elif op == "REPEAT":
                            condition = True
                            count = self.value(head)
                        else:
                            if not head:
                                raise ValueError(f"Empty {op} at line {line}")
                            condition = (self.value(head) == 0) == (op == "IFE")
                    final = block(opening + 1, active and condition, True)
                    for _ in range(count - 1):
                        block(opening + 1, True, True)
                    pos = final
                    continue
                start = pos
                depth = 0
                quoted = False
                while pos < len(src):
                    ch = src[pos]
                    if ch == '"':
                        quoted = not quoted
                    if not quoted:
                        if ch == "<":
                            depth += 1
                        if ch == ">":
                            if depth == 0:
                                break
                            depth -= 1
                        if ch == "\n":
                            break
                    pos += 1
                if active:
                    try:
                        self.statement(src[start:pos], line)
                    except Exception as exc:
                        raise ValueError(f"Line {line}: {src[start:pos]}") from exc
            if end:
                raise ValueError("Unclosed conditional")
            return pos

        block(0)
        result = "\n".join(self.out) + "\n"

        # Explicit NES adaptation points, distinct from dialect conversion.
        def replace(start, end, body):
            nonlocal result
            a = result.index(start)
            b = result.index(end, a)
            result = result[:a] + body + "\n" + result[b:]

        replace(
            "B_LINLIN:", "B_BUFOFS .set", "; INLIN / INCHR are supplied by nes/io.s"
        )
        replace(
            "lda #<(B_MEMORY)",
            "B_ASKAGN:",
            "; Fixed cartridge RAM ceiling; never probe hardware registers.\n"
            "lda #0\nldy #$80\nsta B_MEMSIZ\nsty B_MEMSIZ+1\n"
            "sta B_FRETOP\nsty B_FRETOP+1",
        )
        result = result.replace(
            ".byte 83,84,77,32,66,65,83,73,67,32,86,49,46,49", '.byte "NES BASIC V1.1"'
        )
        return result


if __name__ == "__main__":
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    (build / "basic.s").write_text(
        Converter().run((ROOT / "m6502.asm").read_text()), encoding="ascii"
    )
