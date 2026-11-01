"""Sync publish_files, reweight, verify, and package for Stake upload."""

from __future__ import annotations

import sys
from pathlib import Path

SDK_ROOT = Path(__file__).resolve().parents[2]
GAME_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(GAME_DIR))

from game_config import GameConfig
from gamestate import GameState
from reweight_lut import MODE_COSTS, restore_from_lookup, reweight_all
from src.write_data.write_configs import generate_configs
from utils.rgs_verification import execute_all_tests

PUBLISH = GAME_DIR / "library" / "publish_files"


def main() -> None:
    import os

    os.chdir(SDK_ROOT)
    for mode in MODE_COSTS:
        restore_from_lookup(mode)
        print(f"restored {mode}")

    for name in ("books_max_win_spin.jsonl.zst", "lookUpTable_max_win_spin_0.csv"):
        path = PUBLISH / name
        if path.exists():
            path.unlink()
            print(f"removed {name}")

    for item in reweight_all(restore=False):
        print(
            f"reweight {item['mode']}: {item['rtp_before']:.4f} -> {item['rtp_after']:.4f}"
        )

    config = GameConfig()
    gamestate = GameState(config)
    generate_configs(gamestate)
    print("generate_configs done")

    execute_all_tests(config)
    print("execute_all_tests PASSED")


if __name__ == "__main__":
    main()
