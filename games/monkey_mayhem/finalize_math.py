"""Finalize Monkey Mayhem math: reweight, verify, PAR, package, export story books."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SDK_ROOT = Path(__file__).resolve().parents[2]
GAME_DIR = SDK_ROOT / "games" / "monkey_mayhem"


def main() -> None:
    steps = [
        [sys.executable, str(GAME_DIR / "reweight_lut.py"), "--restore"],
        [sys.executable, "-m", "utils.rgs_verification", "-g", "monkey_mayhem"],
        [sys.executable, str(GAME_DIR / "verify_monkey_mayhem.py")],
        [sys.executable, str(GAME_DIR / "export_story_books.py")],
        [sys.executable, str(GAME_DIR / "package_stake.py")],
    ]
    for cmd in steps:
        print(">>", " ".join(cmd))
        subprocess.run(cmd, cwd=str(SDK_ROOT), check=True)


if __name__ == "__main__":
    main()
