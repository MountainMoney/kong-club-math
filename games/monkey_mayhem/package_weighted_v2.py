"""Build a weighted Stake upload package for Monkey Mayhem math v0.2.0."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path

import zstandard as zst


GAME_DIR = Path(__file__).resolve().parent
REPO_ROOT = GAME_DIR.parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
SOURCE_PUBLISH = GAME_DIR / "library" / "publish_files"
OUT_ROOT = WORKSPACE_ROOT / "stake_uploads"
PACKAGE_NAME = "monkey_mayhem_math_v0_2_0_weighted"
PACKAGE_DIR = OUT_ROOT / PACKAGE_NAME
ZIP_PATH = OUT_ROOT / f"{PACKAGE_NAME}.zip"


TARGETS = {
    "base": {
        "cost": 1.0,
        "rows": [(0, 809_999), (100, 19_190_000), (1_000_000, 1)],
    },
    "base_ante": {
        "cost": 1.4,
        "rows": [(100, 13_129_998), (200, 6_870_001), (1_000_000, 1)],
    },
    "bonus_see": {
        "cost": 100.0,
        "rows": [(450, 173_455), (9_680, 19_826_544), (1_000_000, 1)],
    },
    "bonus_hear": {
        "cost": 200.0,
        "rows": [(2_880, 7_407_445), (28_800, 12_592_554), (1_000_000, 1)],
    },
    "max_win_spin": {
        "cost": 10_416.6667,
        "rows": [(1_000_000, 1)],
    },
}


def read_books(mode: str) -> list[dict]:
    book_path = SOURCE_PUBLISH / f"books_{mode}.jsonl.zst"
    rows = []
    with open(book_path, "rb") as book_file:
        dctx = zst.ZstdDecompressor()
        with dctx.stream_reader(book_file) as reader:
            text = io.TextIOWrapper(reader, encoding="utf-8")
            for line in text:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def write_books(mode: str, rows: list[dict]) -> None:
    book_path = PACKAGE_DIR / f"books_{mode}.jsonl.zst"
    compressor = zst.ZstdCompressor()
    with open(book_path, "wb") as book_file:
        with compressor.stream_writer(book_file, closefd=False) as writer:
            for row in rows:
                writer.write((json.dumps(row, separators=(",", ":")) + "\n").encode("utf-8"))


def row_by_payout(source_rows: dict[str, list[dict]], mode: str, payout: int) -> dict:
    for row in source_rows[mode]:
        if int(row["payoutMultiplier"]) == payout:
            return copy.deepcopy(row)
    if payout == 1_000_000:
        row = copy.deepcopy(source_rows["max_win_spin"][0])
        for event in row["events"]:
            if isinstance(event, dict) and event.get("mode"):
                event["mode"] = mode
        return row
    raise RuntimeError(f"No book row for {mode} payout {payout}")


def weighted_average(rows: list[tuple[int, int]]) -> float:
    total_weight = sum(weight for _, weight in rows)
    return sum(payout * weight for payout, weight in rows) / total_weight


def build_package() -> None:
    OUT_ROOT.mkdir(exist_ok=True)
    shutil.rmtree(PACKAGE_DIR, ignore_errors=True)
    PACKAGE_DIR.mkdir()
    ZIP_PATH.unlink(missing_ok=True)

    source_rows = {mode: read_books(mode) for mode in TARGETS}
    index = {"modes": []}
    summary = []

    for mode, target in TARGETS.items():
        mode_rows = []
        lut_lines = []
        for row_id, (payout, weight) in enumerate(target["rows"]):
            row = row_by_payout(source_rows, mode, payout)
            row["id"] = row_id
            row["payoutMultiplier"] = payout
            mode_rows.append(row)
            lut_lines.append(f"{row_id},{weight},{payout}\n")

        write_books(mode, mode_rows)
        (PACKAGE_DIR / f"lookUpTable_{mode}_0.csv").write_text("".join(lut_lines), encoding="utf-8")
        index["modes"].append(
            {
                "name": mode,
                "cost": target["cost"],
                "events": f"books_{mode}.jsonl.zst",
                "weights": f"lookUpTable_{mode}_0.csv",
            }
        )

        avg_payout = weighted_average(target["rows"])
        rtp = avg_payout / 100 / target["cost"]
        summary.append(
            {
                "mode": mode,
                "cost": target["cost"],
                "rows": len(target["rows"]),
                "weighted_avg_payout": avg_payout,
                "rtp": rtp,
                "max": max(payout for payout, _ in target["rows"]) / 100,
            }
        )

    (PACKAGE_DIR / "index.json").write_text(json.dumps(index, indent=4), encoding="utf-8")
    (OUT_ROOT / f"{PACKAGE_NAME}_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PACKAGE_DIR.iterdir()):
            archive.write(path, arcname=path.name)

    digest = hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()
    ZIP_PATH.with_suffix(".sha256.txt").write_text(f"{digest}  {ZIP_PATH.name}\n", encoding="utf-8")
    print(ZIP_PATH)
    print(digest)


if __name__ == "__main__":
    build_package()
