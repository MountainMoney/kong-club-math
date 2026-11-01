"""Print the Stake-brief verification table from lookup CSVs. Exit 1 on hard fails."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parents[1]
SDK_ROOT = GAME_DIR.parents[1]
sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(GAME_DIR))

from game_config import GameConfig
from game_criteria import BASE_CAP_QUOTA, PEAK_CAP_QUOTA

LOOKUP = GAME_DIR / "library" / "lookup_tables"
PUBLISH = GAME_DIR / "library" / "publish_files"

# Brief role → existing BetMode (do not rename).
MODES = [
    ("base", 1.0),
    ("base_ante", 1.4),
    ("feature_spin", 50.0),
    ("peak_spin", 1000.0),
    ("bonus_see", 100.0),
    ("bonus_hear", 200.0),
    ("bonus_gamble", 1567.0),
]


def lut_path(mode: str) -> Path | None:
    for folder in (PUBLISH, LOOKUP):
        for name in (f"lookUpTable_{mode}_0.csv", f"lookUpTable_{mode}.csv"):
            path = folder / name
            if path.exists():
                return path
    return None


def read_lut(path: Path) -> list[tuple[int, int, float]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            parts = line.strip().split(",")
            if len(parts) < 3:
                continue
            try:
                sim_id, weight, payout = int(parts[0]), int(parts[1]), int(parts[2])
            except ValueError:
                continue
            rows.append((sim_id, weight, payout / 100.0))
    return rows


def criteria_from_books(mode: str) -> dict[int, str]:
    books = GAME_DIR / "library" / "books" / f"books_{mode}.jsonl"
    mapping = {}
    if not books.exists():
        # compressed / json books — skip; quotas still checked via payout shape
        return mapping
    import json

    with books.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                book = json.loads(line)
            except json.JSONDecodeError:
                continue
            mapping[int(book.get("id", -1))] = str(book.get("criteria", ""))
    return mapping


def summarize(mode: str, cost: float, rows: list[tuple[int, int, float]], crit: dict[int, str]) -> dict:
    total_w = sum(w for _, w, _ in rows) or 1
    ev = sum(w * p for _, w, p in rows) / total_w
    rtp = ev / cost
    hits = sum(w for _, w, p in rows if p > 0) / total_w
    ge_cost = sum(w for _, w, p in rows if p + 1e-9 >= cost) / total_w
    caps = [(w, p) for _, w, p in rows if abs(p - 25000) < 1e-6]
    p_cap = sum(w for w, _ in caps) / total_w
    cap_rtp = (25000.0 * p_cap) / cost
    max_p = max((p for _, _, p in rows), default=0.0)
    dead = 0.0
    if crit:
        w_by = defaultdict(float)
        for sim, w, p in rows:
            w_by[crit.get(sim, "")] += w
        dead = w_by.get("dead_juicy", 0.0) / total_w
    else:
        dead = sum(w for _, w, p in rows if p <= 0) / total_w
    return {
        "mode": mode,
        "cost": cost,
        "n_books": len(rows),
        "weighted_rtp": rtp,
        "e_pay_over_cost": ev / cost,
        "hit_rate": hits,
        "p_dead_juicy": dead,
        "p_ge_cost": ge_cost,
        "p_cap": p_cap,
        "cap_rtp_points": cap_rtp * 100.0,
        "max_payout": max_p,
    }


def fail_checks(rows_by_mode: dict[str, dict], cfg: GameConfig) -> list[str]:
    fails = []
    feature = rows_by_mode.get("feature_spin")
    if feature and feature["max_payout"] > float(cfg.wincap) + 1e-6:
        fails.append(f"feature_spin: max {feature['max_payout']} above wincap {cfg.wincap}")
    peak = rows_by_mode.get("peak_spin")
    if peak and peak["n_books"] >= 2000:
        if not (0.90 <= peak["e_pay_over_cost"] <= 0.98):
            fails.append(
                f"peak_spin: E[pay]/cost={peak['e_pay_over_cost']:.4f} not in 0.90–0.98 "
                "(raw sim; optimizer still required for exact 96.01)"
            )
        if abs(peak["p_cap"] - PEAK_CAP_QUOTA) > 0.002 and peak["n_books"] >= 20_000:
            fails.append(f"peak_spin: P(cap)={peak['p_cap']} not ≈ {PEAK_CAP_QUOTA}")
    base = rows_by_mode.get("base")
    if base and base["n_books"] >= 50_000:
        if abs(base["cap_rtp_points"] - 10.0) > 3.0:
            fails.append(f"base: cap RTP share {base['cap_rtp_points']:.2f} not ≈ 10")
        if abs(base["weighted_rtp"] - cfg.rtp) > 0.04:
            fails.append(f"base: weighted RTP {base['weighted_rtp']:.4f} not ≈ 0.9601")
    return fails


def main() -> int:
    cfg = GameConfig()
    print("Monkey Mayhem Stake-brief verification")
    print("Mode map: ante=base_ante feature=feature_spin summit=peak_spin")
    print("          bonus_3=bonus_see bonus_4=bonus_hear gamble=bonus_gamble")
    print(
        f"{'mode':<14} {'n':>8} {'RTP':>8} {'E/c':>8} {'hit':>7} {'dead':>7} "
        f"{'>=c':>7} {'Pcap':>8} {'capPts':>7} {'max':>8}"
    )
    summaries = {}
    for mode, cost in MODES:
        path = lut_path(mode)
        if path is None:
            print(f"{mode:<14} MISSING LUT")
            continue
        rows = read_lut(path)
        crit = criteria_from_books(mode)
        s = summarize(mode, cost, rows, crit)
        summaries[mode] = s
        print(
            f"{s['mode']:<14} {s['n_books']:8d} {s['weighted_rtp']*100:7.2f}% "
            f"{s['e_pay_over_cost']:8.3f} {s['hit_rate']:7.3f} {s['p_dead_juicy']:7.3f} "
            f"{s['p_ge_cost']:7.3f} {s['p_cap']:8.5f} {s['cap_rtp_points']:7.2f} {s['max_payout']:8.1f}"
        )
    fails = fail_checks(summaries, cfg)
    if fails:
        print("FAIL")
        for line in fails:
            print(" -", line)
        return 1
    print("PASS (hard gates). Raw 2k RTP is not the LUT target — run optimizer for 96.01%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
