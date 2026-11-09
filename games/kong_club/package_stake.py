"""Package Kong Club publish_files for Stake Engine upload."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


GAME_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = GAME_DIR.parents[2]
SOURCE_PUBLISH = GAME_DIR / "library" / "publish_files"
OUT_ROOT = WORKSPACE_ROOT / "stake_uploads"
VERSION = "v0_4_0_250k"
PACKAGE_NAME = f"kong_club_math_{VERSION}"
PACKAGE_DIR = OUT_ROOT / PACKAGE_NAME
ZIP_PATH = OUT_ROOT / f"{PACKAGE_NAME}.zip"

REQUIRED_MODES = [
    "base",
    "base_ante",
    "feature_spin",
    "peak_spin",
    "bonus_see",
    "bonus_hear",
    "bonus_mystery",
]
MIN_ROWS = 250_000
STAKE_SLUG = "kong-club"


def count_lut_rows(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def apply_stake_slug(package_dir: Path) -> None:
    for name in ("config.json", "math_config.json"):
        path = package_dir / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if "gameID" in data:
            data["gameID"] = STAKE_SLUG
        if "game_id" in data:
            data["game_id"] = STAKE_SLUG
        path.write_text(json.dumps(data, indent=4), encoding="utf-8")


def build_package() -> None:
    if not SOURCE_PUBLISH.exists():
        raise RuntimeError(f"Missing publish folder: {SOURCE_PUBLISH}")

    index_path = SOURCE_PUBLISH / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    mode_names = [mode["name"] for mode in index["modes"]]
    if mode_names != REQUIRED_MODES:
        raise RuntimeError(f"Unexpected modes in index.json: {mode_names}")

    for mode in REQUIRED_MODES:
        lut = SOURCE_PUBLISH / f"lookUpTable_{mode}_0.csv"
        books = SOURCE_PUBLISH / f"books_{mode}.jsonl.zst"
        if not lut.exists() or not books.exists():
            raise RuntimeError(f"Missing publish artifact for {mode}")
        rows = count_lut_rows(lut)
        if rows < MIN_ROWS:
            raise RuntimeError(f"{mode} has {rows} rows; expected at least {MIN_ROWS}")

    subprocess.check_call([sys.executable, str(GAME_DIR / "stake_diversity_check.py")], cwd=str(GAME_DIR))

    OUT_ROOT.mkdir(exist_ok=True)
    shutil.rmtree(PACKAGE_DIR, ignore_errors=True)
    shutil.copytree(SOURCE_PUBLISH, PACKAGE_DIR)
    for path in list(PACKAGE_DIR.iterdir()):
        if "max_win_spin" in path.name:
            path.unlink()
    apply_stake_slug(PACKAGE_DIR)
    ZIP_PATH.unlink(missing_ok=True)

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PACKAGE_DIR.iterdir()):
            archive.write(path, arcname=path.name)

    digest = hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()
    ZIP_PATH.with_suffix(".sha256.txt").write_text(f"{digest}  {ZIP_PATH.name}\n", encoding="utf-8")
    print(ZIP_PATH)
    print(digest)


if __name__ == "__main__":
    build_package()
