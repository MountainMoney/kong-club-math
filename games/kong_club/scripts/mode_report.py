"""Per-mode report from the published 500-book library."""

from __future__ import annotations

import io
import json
from collections import defaultdict
from pathlib import Path

import zstandard

GAME = Path(__file__).resolve().parents[1]
PUBLISH = GAME / "library" / "publish_files"


def read_lut(mode: str) -> list[tuple[int, int, int]]:
    path = PUBLISH / f"lookUpTable_{mode}_0.csv"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sim_id, weight, payout = line.split(",")
        rows.append((int(sim_id), int(weight), int(payout)))
    return rows


def read_books(mode: str) -> list[dict]:
    path = PUBLISH / f"books_{mode}.jsonl.zst"
    books = []
    with path.open("rb") as handle:
        text = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(handle), encoding="utf-8")
        for line in text:
            if line.strip():
                books.append(json.loads(line))
    return books


def main() -> None:
    index = json.loads((PUBLISH / "index.json").read_text(encoding="utf-8"))
    report = []
    for mode in index["modes"]:
        name = mode["name"]
        cost = float(mode["cost"])
        rows = read_lut(name)
        books = read_books(name)
        by_id = {int(book["id"]): book for book in books}
        total_w = sum(weight for _sid, weight, _pay in rows)
        win_x = sum(weight * payout for _sid, weight, payout in rows) / total_w / 100.0
        rtp = win_x / cost
        hit_w = sum(weight for _sid, weight, payout in rows if payout > 0)
        dead_w = sum(weight for _sid, weight, payout in rows if payout <= 0)
        max_x = max(payout for _sid, _weight, payout in rows) / 100.0
        caps = 0
        upgrades = 0
        hear_books = 0
        speak_direct = []
        bonus_wins = []
        for book in books:
            events = book.get("events") or []
            caps += int(any(
                event.get("type") == "boardActivation" and (event.get("coinFeature") or {}).get("capHit")
                for event in events
            ))
            states = [str(event.get("state") or "") for event in events if event.get("type") == "kongClubMode"]
            if any(state == "upgrade_bonus_speak" for state in states):
                upgrades += 1
            started_hear = any(state.endswith("_hear") or state == "upgrade_bonus_hear" for state in states)
            started_speak = any(state.endswith("_speak") and "upgrade" not in state for state in states)
            if started_hear or name == "bonus_hear":
                hear_books += 1
            if started_speak or (name == "bonus_mystery" and book.get("criteria") == "pick_speak") or (
                name == "bonus_risky" and book.get("criteria") == "risky_speak"
            ):
                speak_direct.append(book["payoutMultiplier"] / 100.0)
            if book.get("criteria") in {"freegame", "bonus_see", "bonus_hear", "pick_see", "pick_hear", "pick_speak", "risky_hear", "risky_speak"} or any(
                state.startswith("start_bonus_") or state.startswith("organic_bonus_") for state in states
            ):
                bonus_wins.append(book["payoutMultiplier"] / 100.0)
        row = {
            "mode": name,
            "cost": cost,
            "books": len(books),
            "rtp": round(rtp, 6),
            "hit_rate": round(hit_w / total_w, 6),
            "dead_rate": round(dead_w / total_w, 6),
            "max_win": max_x,
            "avg_bonus_win": round(sum(bonus_wins) / len(bonus_wins), 4) if bonus_wins else None,
            "bonus_books": len(bonus_wins),
            "speak_direct_avg": round(sum(speak_direct) / len(speak_direct), 4) if speak_direct else None,
            "speak_direct_books": len(speak_direct),
            "hear_to_speak_upgrades": upgrades,
            "hear_books_scanned": hear_books,
            "coin_cap_hits": caps,
        }
        report.append(row)
        print(
            f"{name:14} cost {cost:10.4f}  RTP {rtp*100:7.3f}%  hit {row['hit_rate']*100:6.2f}%  "
            f"dead {row['dead_rate']*100:6.2f}%  max {max_x:8.1f}x  books {len(books)}  caps {caps}"
        )
    out = GAME / "reports" / "locked_spec_963.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
