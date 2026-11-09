"""Generate local FE math-books cache for Kong Club (Phase A).

Base / Extra Chance include freegame samples at certified quotas so Extra Chance
actually triggers local bonuses (warm cache previously forced criteria=basegame only).
"""
from __future__ import annotations

import contextlib
import io
import json
import random
import statistics
import time
from pathlib import Path
import sys

GAME_ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = Path(__file__).resolve().parents[3]
WEB_CACHE = (
    Path(__file__).resolve().parents[4]
    / "web-sdk"
    / "apps"
    / "kong_club"
    / ".cache"
    / "math-books"
)
PUBLISH = GAME_ROOT / "library" / "publish_files"

sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(GAME_ROOT))

from game_config import GameConfig
from gamestate import GameState

MODE_SPINS = {
    "base": 400,
    "base_ante": 400,
    "hunt_2": 80,
    "hunt_3": 80,
    "hunt_4": 80,
    "hunt_5": 80,
    "hunt_6": 80,
    "feature_spin": 80,
    "peak_spin": 80,
    "bonus_see": 50,
    "bonus_hear": 50,
    "bonus_mystery": 80,
    "bonus_risky": 80,
}

MODE_CRITERIA = {
    "base": "basegame",
    "base_ante": "basegame",
    "hunt_2": "basegame",
    "hunt_3": "basegame",
    "hunt_4": "basegame",
    "hunt_5": "basegame",
    "hunt_6": "basegame",
    "feature_spin": "run",
    "peak_spin": "live",
    "bonus_see": "bonus_see",
    "bonus_hear": "bonus_hear",
    "bonus_mystery": "pick_see",
    "bonus_risky": "risky_dead",
}


def zst_mtime_ms(mode: str) -> float:
    path = PUBLISH / f"books_{mode}.jsonl.zst"
    if not path.exists():
        return 0.0
    return path.stat().st_mtime * 1000.0


def max_level_from_book(book: dict) -> int:
    max_lvl = 0
    for event in book.get("events", []):
        if event.get("type") != "updateLevelUpTiles":
            continue
        for col in event.get("tileLevels") or []:
            for value in col:
                if isinstance(value, (int, float)):
                    max_lvl = max(max_lvl, int(value))
    return max_lvl


def book_has_type(book: dict, event_type: str) -> bool:
    return any(event.get("type") == event_type for event in book.get("events", []))


def _coin_feature_items(event: dict) -> list[dict]:
    feature = event.get("coinFeature") or {}
    items = list(feature.get("items") or [])
    rounds = feature.get("rounds")
    if isinstance(rounds, list):
        for round_data in rounds:
            items.extend(list((round_data or {}).get("items") or []))
    return items


def book_has_coin_kind(book: dict, kind: str) -> bool:
    for event in book.get("events", []):
        if event.get("type") != "boardActivation":
            continue
        if any(item.get("kind") == kind for item in _coin_feature_items(event)):
            return True
    return False


def book_is_freegame(book: dict) -> bool:
    return any(
        event.get("type") == "freeSpinTrigger"
        or (
            event.get("type") == "kongClubMode"
            and (
                str(event.get("state", "")).startswith("organic_bonus_")
                or str(event.get("state", "")).startswith("start_bonus_")
            )
        )
        for event in book.get("events", [])
    )


def _freegame_quota(config: GameConfig, mode: str) -> float:
    if mode == "base_ante":
        return float(config.bonus_hit_rate_ante)
    if mode == "base":
        return float(config.bonus_hit_rate_base)
    return 0.0


def generate_mode(mode: str, n: int) -> tuple[list[dict], list[dict]]:
    """Return (books, lut_entries). LUT weights match certified freegame quotas."""
    GameConfig._instance = None
    config = GameConfig()
    books: list[dict] = []
    sink = io.StringIO()
    quota = _freegame_quota(config, mode)

    if mode == "feature_spin":
        criteria_list = ["run"] * n
        rng = random.Random(303)
        rng.shuffle(criteria_list)
        n_fg = 0
        n_bg = n
    elif mode == "peak_spin":
        n_dead = int(round(n * 0.50))
        n_live = n - n_dead
        criteria_list = ["dead_juicy"] * n_dead + ["live"] * n_live
        rng = random.Random(505)
        rng.shuffle(criteria_list)
        n_fg = 0
        n_bg = n
    elif mode == "bonus_mystery":
        n_see = int(round(n * 0.50))
        n_hear = int(round(n * 0.45))
        n_speak = max(0, n - n_see - n_hear)
        criteria_list = ["pick_see"] * n_see + ["pick_hear"] * n_hear + ["pick_speak"] * n_speak
        rng = random.Random(404)
        rng.shuffle(criteria_list)
        n_fg = 0
        n_bg = n
    elif mode == "bonus_risky":
        n_dead = int(round(n * 0.50))
        n_hear = int(round(n * 0.40))
        n_speak = max(0, n - n_dead - n_hear)
        criteria_list = ["risky_dead"] * n_dead + ["risky_hear"] * n_hear + ["risky_speak"] * n_speak
        rng = random.Random(414)
        rng.shuffle(criteria_list)
        n_fg = 0
        n_bg = n
    elif mode in ("base", "base_ante") and quota > 0:
        # Enough freegame samples to feel Extra Chance in local play, weighted to quota.
        n_fg = max(8, int(round(n * quota * 8)))  # oversample then down-weight
        n_fg = min(n_fg, max(1, n // 4))
        n_bg = n - n_fg
        criteria_list = ["basegame"] * n_bg + ["freegame"] * n_fg
        rng = random.Random(101 + len(mode) * 17)
        rng.shuffle(criteria_list)
    else:
        criteria_list = [MODE_CRITERIA[mode]] * n
        n_fg = 0
        n_bg = n

    with contextlib.redirect_stdout(sink):
        for i, criteria in enumerate(criteria_list):
            gs = GameState(config)
            gs.betmode = mode
            gs.criteria = criteria
            gs.run_spin(i)
            book = gs.book.to_json()
            book["id"] = i
            books.append(book)

    # Weight so P(pick freegame book) ≈ quota when using weighted LUT.
    if mode in ("base", "base_ante") and n_fg > 0 and n_bg > 0:
        # fg_total / (bg_total + fg_total) = quota
        # bg_total = n_bg * w_bg, set w_bg = 1 → fg_total = quota * n_bg / (1 - quota)
        w_bg = 1.0
        fg_total = quota * n_bg / max(1e-9, 1.0 - quota)
        w_fg = fg_total / n_fg
        lut = []
        for i, book in enumerate(books):
            is_fg = book_is_freegame(book)
            weight = w_fg if is_fg else w_bg
            payout = int(round(float(book.get("payoutMultiplier", 0))))
            lut.append({"index": i, "weight": weight, "payout": payout})
    else:
        lut = [
            {
                "index": i,
                "weight": 1.0,
                "payout": int(round(float(book.get("payoutMultiplier", 0)))),
            }
            for i, book in enumerate(books)
        ]

    return books, lut


def write_lut_csv(path: Path, lut: list[dict]) -> None:
    lines = [f"{entry['index']},{entry['weight']},{entry['payout']}" for entry in lut]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize(mode: str, books: list[dict], lut: list[dict]) -> dict:
    n = len(books)
    ba = sum(1 for b in books if book_has_type(b, "boardActivation"))
    multi = sum(1 for b in books if book_has_coin_kind(b, "multiplier"))
    collector = sum(1 for b in books if book_has_coin_kind(b, "collector"))
    cs = sum(1 for b in books if book_has_type(b, "coinSeed"))
    sw = sum(1 for b in books if book_has_type(b, "stickyWilds"))
    fg = sum(1 for b in books if book_is_freegame(b))
    max_lvls = [max_level_from_book(b) for b in books]
    payouts = [b.get("payoutMultiplier", 0) / 100.0 for b in books]
    payouts_sorted = sorted(payouts)
    med = statistics.median(payouts_sorted) if payouts_sorted else 0.0

    total_w = sum(float(e["weight"]) for e in lut) or 1.0
    fg_w = sum(
        float(e["weight"]) for e, b in zip(lut, books) if book_is_freegame(b)
    )
    return {
        "mode": mode,
        "count": n,
        "freegame_books": fg,
        "freegame_pick_pct": round(100.0 * fg_w / total_w, 2),
        "boardActivation_pct": round(100.0 * ba / n, 1) if n else 0.0,
        "multi_books": multi,
        "collector_books": collector,
        "coinSeed_pct": round(100.0 * cs / n, 1) if n else 0.0,
        "stickyWilds_pct": round(100.0 * sw / n, 1) if n else 0.0,
        "updateLevelUpTiles_max_level": max(max_lvls) if max_lvls else 0,
        "payout_avg": round(sum(payouts) / n, 3) if n else 0.0,
        "payout_median": round(med, 3),
        "payout_max": round(max(payouts), 3) if payouts else 0.0,
    }


def main() -> None:
    WEB_CACHE.mkdir(parents=True, exist_ok=True)
    meta_path = WEB_CACHE / ".meta.json"
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    requested = [mode for mode in sys.argv[1:] if mode in MODE_SPINS]
    modes = requested or list(MODE_SPINS)

    all_stats = []
    now_ms = int(time.time() * 1000)
    for mode in modes:
        n = MODE_SPINS[mode]
        print(f"Generating {mode}: {n} spins...")
        books, lut = generate_mode(mode, n)
        out = WEB_CACHE / f"books_{mode}.json"
        out.write_text(json.dumps(books, separators=(",", ":")), encoding="utf-8")
        lut_path = WEB_CACHE / f"lookUpTable_{mode}_0.csv"
        write_lut_csv(lut_path, lut)
        source_mtime = zst_mtime_ms(mode)
        meta[mode] = {
            "sourceMtimeMs": source_mtime,
            "cachedAt": now_ms,
            "hasCacheLut": True,
        }
        stats = summarize(mode, books, lut)
        all_stats.append(stats)
        print(
            f"  count={stats['count']}  freegame_books={stats['freegame_books']}  "
            f"freegame_pick~{stats['freegame_pick_pct']}%  "
            f"boardActivation={stats['boardActivation_pct']}%  "
            f"MULTI={stats['multi_books']}  COLLECTOR={stats['collector_books']}  "
            f"coinSeed={stats['coinSeed_pct']}%  "
            f"payout avg/med/max={stats['payout_avg']}/{stats['payout_median']}/{stats['payout_max']}"
        )

    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("Wrote", meta_path)
    print("CACHE_STATS")
    print(json.dumps(all_stats, indent=2))


if __name__ == "__main__":
    main()
