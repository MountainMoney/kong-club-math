"""Sync publish artifacts, reweight, verify, and package v0.4 (5 modes, no max win spin)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent
SDK_ROOT = GAME_DIR.parents[1]
PUBLISH = GAME_DIR / "library" / "publish_files"
LOOKUP = GAME_DIR / "library" / "lookup_tables"
MODES = ["base", "base_ante", "feature_spin", "bonus_see", "bonus_hear"]
STALE_PREFIXES = ("max_win_spin", "books_max_win_spin", "lookUpTable_max_win_spin")


def cleanup_stale_publish() -> None:
    for path in PUBLISH.iterdir():
        if any(path.name.startswith(prefix) or "max_win_spin" in path.name for prefix in STALE_PREFIXES):
            path.unlink(missing_ok=True)


def sync_lookup_to_publish() -> None:
    for mode in MODES:
        src = LOOKUP / f"lookUpTable_{mode}.csv"
        dst = PUBLISH / f"lookUpTable_{mode}_0.csv"
        if not src.exists():
            raise RuntimeError(f"Missing lookup table: {src}")
        shutil.copy2(src, dst)


def verify_books() -> None:
    for mode in MODES:
        books = PUBLISH / f"books_{mode}.jsonl.zst"
        lut = PUBLISH / f"lookUpTable_{mode}_0.csv"
        if not books.exists():
            raise RuntimeError(f"Missing books: {books}")
        rows = sum(1 for _ in lut.open(encoding="utf-8"))
        if rows < 250_000:
            raise RuntimeError(f"{mode} LUT has {rows} rows; need 250_000")


def tail_metrics() -> None:
    subprocess.check_call([sys.executable, str(GAME_DIR / "stake_star_metrics.py")], cwd=str(GAME_DIR))


def main() -> None:
    sys.path.insert(0, str(SDK_ROOT))
    sys.path.insert(0, str(GAME_DIR))

    cleanup_stale_publish()
    sync_lookup_to_publish()
    verify_books()

    from reweight_lut import reweight_all

    reweight_all(restore=True, modes=MODES)

    from game_config import GameConfig
    from gamestate import GameState
    from src.write_data.write_configs import generate_configs

    generate_configs(GameState(GameConfig()))

    cleanup_stale_publish()
    index = json.loads((PUBLISH / "index.json").read_text(encoding="utf-8"))
    names = [m["name"] for m in index["modes"]]
    if names != MODES:
        raise RuntimeError(f"index.json modes {names} != {MODES}")

    from utils.rgs_verification import execute_all_tests

    prev_cwd = Path.cwd()
    try:
        os.chdir(SDK_ROOT)
        execute_all_tests(GameConfig())
    finally:
        os.chdir(prev_cwd)
    tail_metrics()
    subprocess.check_call([sys.executable, str(GAME_DIR / "package_stake.py")], cwd=str(GAME_DIR))
    print("Ship v0.4 complete.")


if __name__ == "__main__":
    main()
