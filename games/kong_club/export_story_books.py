"""Export representative books from force records for web-sdk Storybook."""

from __future__ import annotations

import io
import json
from pathlib import Path

import zstandard as zst

GAME_DIR = Path(__file__).resolve().parent
LIBRARY = GAME_DIR / "library"
FORCES = LIBRARY / "forces"
PUBLISH = LIBRARY / "publish_files"
OUT = Path(__file__).resolve().parents[3] / "web-sdk" / "apps" / "kong_club" / "src" / "stories" / "data" / "math_books"


def read_book(mode: str) -> dict[int, dict]:
    path = PUBLISH / f"books_{mode}.jsonl.zst"
    rows: dict[int, dict] = {}
    with path.open("rb") as handle:
        dctx = zst.ZstdDecompressor()
        with dctx.stream_reader(handle) as reader:
            text = io.TextIOWrapper(reader, encoding="utf-8")
            for line in text:
                if line.strip():
                    row = json.loads(line)
                    rows[int(row["id"])] = row
    return rows


def export_mode(mode: str, force_path: Path) -> None:
    if not force_path.exists():
        return
    books = read_book(mode)
    force_rows = json.loads(force_path.read_text(encoding="utf-8"))
    exported = []
    for entry in force_rows:
        label = "_".join(f"{item['name']}-{item['value']}" for item in entry.get("search", []))
        for book_id in entry.get("bookIds", [])[:3]:
            if book_id in books:
                exported.append({"label": label, "book": books[book_id]})
    if exported:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{mode}_forced.json").write_text(json.dumps(exported, indent=2), encoding="utf-8")


def main() -> None:
    modes = [
        "base",
        "base_ante",
        "feature_spin",
        "peak_spin",
        "bonus_see",
        "bonus_hear",
        "bonus_gamble",
    ]
    for mode in modes:
        export_mode(mode, FORCES / f"force_record_{mode}.json")
    index = {
        "modes": modes,
        "outputDir": str(OUT),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
