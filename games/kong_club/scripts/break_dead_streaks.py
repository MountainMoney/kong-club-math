"""Break id-order dead runs longer than 10 in the base and Ante books.

The replacement is a real 0.2x–0.5x cluster, not a lookup-only payout.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import zstandard

GAME = Path(__file__).resolve().parents[1]
ROOT = GAME.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(GAME))

from game_config import GameConfig  # noqa: E402
from gamestate import GameState  # noqa: E402

PUBLISH = GAME / "library" / "publish_files"
MAX_RUN = 10


def read_books(mode: str) -> list[dict]:
    path = PUBLISH / f"books_{mode}.jsonl.zst"
    books = []
    with path.open("rb") as handle:
        text = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(handle), encoding="utf-8")
        for line in text:
            if line.strip():
                books.append(json.loads(line))
    return books


def write_books(mode: str, books: list[dict]) -> None:
    books = sorted(books, key=lambda book: int(book["id"]))
    payload = "".join(json.dumps(book, separators=(",", ":")) + "\n" for book in books)
    compressed = zstandard.ZstdCompressor().compress(payload.encode("utf-8"))
    (PUBLISH / f"books_{mode}.jsonl.zst").write_bytes(compressed)


def longest_dead(books: list[dict]) -> int:
    ordered = sorted(books, key=lambda book: int(book["id"]))
    best = run = 0
    for book in ordered:
        if int(book.get("payoutMultiplier") or 0) <= 0:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def tiny_book(gs: GameState, book_id: int, mode: str) -> dict:
    for attempt in range(12):
        gs.betmode = mode
        gs.criteria = "basegame"
        gs.force_tiny_hit = True
        gs.run_spin(book_id, simulation_seed=book_id + 1 + attempt * 10007)
        book = gs.book.to_json()
        pay = int(book["payoutMultiplier"])
        if book.get("criteria") == "basegame" and 19 <= pay <= 55:
            book["id"] = book_id
            return book
    raise RuntimeError(f"could not plant a 0.2x–0.5x break for book {book_id}")


def break_mode(mode: str, gs: GameState) -> list[int]:
    books = read_books(mode)
    ordered = sorted(books, key=lambda book: int(book["id"]))
    by_id = {int(book["id"]): book for book in ordered}
    run = 0
    replaced: list[int] = []
    # Ante uses the same base-like planter. The betmode still has to be the
    # mode being edited so the book criteria and events stay on that mode.
    gs.betmode = mode
    for book in ordered:
        if int(book.get("payoutMultiplier") or 0) <= 0 and book.get("criteria") == "basegame":
            run += 1
        else:
            run = 0
            continue
        if run == MAX_RUN + 1:
            book_id = int(book["id"])
            by_id[book_id] = tiny_book(gs, book_id, mode)
            replaced.append(book_id)
            run = 0
    if replaced:
        write_books(mode, list(by_id.values()))
    print(f"{mode}: longest dead {longest_dead(read_books(mode) if replaced else books)}  replaced {replaced}")
    return replaced


def main() -> None:
    gs = GameState(GameConfig())
    replaced = {}
    for mode in ("base", "base_ante"):
        replaced[mode] = break_mode(mode, gs)
    out = GAME / "reports" / "streak_breaks.json"
    out.write_text(json.dumps(replaced) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
