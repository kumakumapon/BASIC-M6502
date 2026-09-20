"""Install project-local Windows tools after verifying pinned archive hashes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emulators", action="store_true")
    parser.add_argument("--tests", action="store_true")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error(
            "These archives are for Windows. On other OSes build the pinned cc65 source; see docs/NES.md."
        )
    target = ROOT / ".tools"
    target.mkdir(exist_ok=True)
    lock = json.loads((ROOT / "tools.lock.json").read_text())
    for name in ["cc65"] + (["mesen", "fceux"] if args.emulators else []):
        item = lock[name]
        archive = target / item["archive"]
        if not archive.exists():
            temporary = archive.with_suffix(".download")
            subprocess.run(
                [
                    "curl.exe",
                    "--fail",
                    "--location",
                    "--retry",
                    "3",
                    item["url"],
                    "--output",
                    str(temporary),
                ],
                check=True,
            )
            digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
            if digest != item["sha256"]:
                raise SystemExit(
                    f"{name}: archive hash mismatch ({digest}). Nothing extracted. "
                    "The rolling cc65 snapshot may have changed; see docs/NES.md."
                )
            temporary.replace(archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != item["sha256"]:
            raise SystemExit(f"{archive}: hash mismatch; refusing to extract")
        dest = target / item["directory"]
        with zipfile.ZipFile(archive) as z:
            for entry in z.infolist():
                if not (dest / entry.filename).resolve().is_relative_to(dest.resolve()):
                    raise SystemExit("Unsafe archive path: " + entry.filename)
            z.extractall(dest)
        print(f'{name}: {item["version"]}, SHA256 verified')
    if args.emulators:
        # An adjacent settings.json enables portable mode, avoiding user settings.
        settings = target / lock["mesen"]["directory"] / "settings.json"
        if not settings.exists():
            settings.write_text("{}", encoding="utf-8")
    if args.tests:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--target",
                str(target / "python"),
                "py65==" + lock["py65"]["version"],
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
