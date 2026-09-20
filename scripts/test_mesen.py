"""Run the linked ROM under Mesen CE's actual NES CPU/PPU/MMC1 core."""

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_runtime import symbols

PLAIN = [
    0,
    13,
    91,
    93,
    0,
    0,
    92,
    3,
    0,
    64,
    58,
    59,
    95,
    47,
    45,
    94,
    0,
    79,
    76,
    75,
    46,
    44,
    80,
    48,
    0,
    73,
    85,
    74,
    77,
    78,
    57,
    56,
    0,
    89,
    71,
    72,
    66,
    86,
    55,
    54,
    0,
    84,
    82,
    68,
    70,
    67,
    53,
    52,
    0,
    87,
    83,
    65,
    88,
    90,
    69,
    51,
    0,
    3,
    81,
    0,
    0,
    0,
    49,
    50,
    0,
    0,
    0,
    0,
    0,
    32,
    8,
    0,
]
SHIFT = PLAIN.copy()
for i, v in {
    10: 42,
    11: 43,
    13: 63,
    14: 61,
    20: 62,
    21: 60,
    30: 41,
    31: 40,
    38: 39,
    39: 38,
    46: 37,
    47: 36,
    55: 35,
    62: 33,
    63: 34,
}.items():
    SHIFT[i] = v


def keycodes(text):
    result = []
    for c in text:
        code = ord(c)
        result.append([PLAIN.index(code)] if code in PLAIN else [SHIFT.index(code), 60])
    return result


def cases():
    result = []

    def add(text, expect=(), reject=(" ERROR",), interrupt=False):
        result.append(
            dict(
                text=text + "\r",
                keys=keycodes(text + "\r"),
                expect=list(expect),
                reject=list(reject),
                interrupt=interrupt,
            )
        )

    add("PRINT 1+2", ["\r\n 3 "])
    add('PRINT "HELLO NES"', ["\r\nHELLO NES"])
    add("PRINT 1.5*2.5", ["\r\n 3.75 "])
    add("10 DIM A(3):S=0")
    add("20 FOR I=1 TO 3:A(I)=I*2:S=S+A(I):NEXT I")
    add("30 GOSUB 100:PRINT S:END")
    add("100 S=S+1:RETURN")
    add("RUN", ["\r\n 13 "])
    add("100 S=S+2:RETURN")
    add("LIST", ["100 S=S+2:RETURN"])
    add("RUN", ["\r\n 14 "])
    add("100")
    add("LIST", reject=["100 S=", " ERROR"])
    add("NEW")
    add("PRINT 1/0", ["?/0 ERROR"], reject=[])
    add("DIM A(10000)", ["?OM ERROR"], reject=[])
    add("NEW")
    add('10 A$="":FOR I=1 TO 500:A$=RIGHT$(A$+"1234567890",100):NEXT I')
    add('20 PRINT LEN(A$):PRINT "GC OK"')
    add("RUN", ["\r\n 100 ", "\r\nGC OK"])
    add("PRINT 1+9\b2", ["\r\n 3 "])
    add("REM " + "X" * 260)
    add("FOR I=1 TO 35:PRINT I:NEXT I", [" 35 "])
    add("NEW")
    add("10 GOTO 10")
    add("RUN", ["BREAK IN  10"], interrupt=True)
    add('PRINT "NES TESTS PASSED"', ["\r\nNES TESTS PASSED"])
    return result


def lua_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "{" + ",".join(map(lua_value, value)) + "}"
    return (
        "{"
        + ",".join("[" + lua_value(k) + "]=" + lua_value(v) for k, v in value.items())
        + "}"
    )


def main():
    exe = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else ROOT / ".tools/Mesen_2.2.1_Windows/Mesen.exe"
    )
    out = ROOT / "build"
    # Only configure our project-local portable installation.
    if ROOT / ".tools" in exe.resolve().parents:
        config = exe.parent / "settings.json"
        data = (
            json.loads(config.read_text(encoding="utf-8-sig"))
            if config.exists()
            else {}
        )
        data.setdefault("Debug", {}).setdefault("ScriptWindow", {})[
            "AllowIoOsAccess"
        ] = True
        config.write_text(json.dumps(data), encoding="utf-8")
    script = out / "mesen-test.lua"
    script.write_text(
        "local SYM="
        + lua_value(symbols())
        + "\nlocal OUTPUT_DIR="
        + lua_value(out.as_posix())
        + "\nlocal CASES="
        + lua_value(cases())
        + "\n"
        + (ROOT / "tests/mesen.lua").read_text(),
        encoding="utf-8",
    )
    result = out / "mesen-result.txt"
    if result.exists():
        result.unlink()
    proc = subprocess.run(
        [
            str(exe.resolve()),
            "--testRunner",
            "--timeout=60",
            str(script),
            str(out / "basic.nes"),
        ],
        capture_output=True,
        timeout=75,
    )
    (out / "mesen-process.log").write_bytes(proc.stdout + proc.stderr)
    print(
        result.read_text()
        if result.exists()
        else "No result; see build/mesen-process.log"
    )
    if (
        proc.returncode
        or not result.exists()
        or not result.read_text().startswith("PASS")
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
