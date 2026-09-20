"""Run independent FCEUX verification with an ASCII input hook (Windows)."""

from pathlib import Path
import subprocess
import sys
from test_mesen import ROOT, symbols, cases, lua_value


def main():
    exe = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".tools/fceux/fceux64.exe"
    out = ROOT / "build"
    script = out / "fceux-test.lua"
    script.write_text(
        "local SYM="
        + lua_value(symbols())
        + "\nlocal OUTPUT_DIR="
        + lua_value(out.as_posix())
        + "\nlocal CASES="
        + lua_value(cases())
        + "\n"
        + (ROOT / "tests/fceux.lua").read_text(),
        encoding="ascii",
    )
    result = out / "fceux-result.txt"
    if result.exists():
        result.unlink()
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    proc = subprocess.run(
        [str(exe.resolve()), "-lua", str(script), str(out / "basic.nes")],
        cwd=exe.resolve().parent,
        capture_output=True,
        timeout=90,
        startupinfo=startup,
    )
    (out / "fceux-process.log").write_bytes(proc.stdout + proc.stderr)
    print(
        result.read_text()
        if result.exists()
        else "No result; see build/fceux-process.log"
    )
    if (
        proc.returncode
        or not result.exists()
        or not result.read_text().startswith("PASS")
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
