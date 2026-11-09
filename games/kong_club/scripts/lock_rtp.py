"""Set buy prices and lookup weights so every mode publishes at 96.3% RTP.

Solved modes (feature, trifecta, buys) keep their book mix and take
cost = mean win / 0.963. Fixed-cost modes (base, ante, hunt) keep their
costs and move lookup weight onto the certified mix.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parents[1]
SDK_ROOT = GAME_DIR.parents[1]
sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(GAME_DIR))

from game_config import HUNT_COSTS, GameConfig  # noqa: E402
from game_criteria import TARGET_RTP  # noqa: E402

PUBLISH = GAME_DIR / "library" / "publish_files"
LOOKUP = GAME_DIR / "library" / "lookup_tables"
TOTAL = 10_000_000_000
SOLVED = {
    "feature_spin",
    "peak_spin",
    "bonus_see",
    "bonus_hear",
    "bonus_mystery",
    "bonus_risky",
}


def read_lut(path: Path) -> list[tuple[int, int, int]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sim_id, weight, payout = line.split(",")
        rows.append((int(sim_id), int(weight), int(payout)))
    return rows


def write_lut(path: Path, rows: list[tuple[int, int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{sim_id},{weight},{payout}\n" for sim_id, weight, payout in rows), encoding="utf-8")


def lut_paths(mode: str) -> list[Path]:
    names = [
        PUBLISH / f"lookUpTable_{mode}_0.csv",
        PUBLISH / f"lookUpTable_{mode}.csv",
        LOOKUP / f"lookUpTable_{mode}.csv",
        LOOKUP / f"lookUpTable_{mode}_0.csv",
    ]
    return [path for path in names if path.exists()]


def load_criteria(mode: str) -> dict[int, str]:
    books = PUBLISH / f"books_{mode}.jsonl.zst"
    import io
    import zstandard

    found: dict[int, str] = {}
    with books.open("rb") as handle:
        text = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(handle), encoding="utf-8")
        for line in text:
            if not line.strip():
                continue
            book = json.loads(line)
            found[int(book["id"])] = str(book.get("criteria") or "basegame")
    return found


def mean_x(payouts: list[int]) -> float:
    return (sum(payouts) / len(payouts) / 100.0) if payouts else 0.0


def rtp_of(rows: list[tuple[int, int, int]], cost: float) -> float:
    total_w = sum(weight for _, weight, _ in rows)
    avg = sum(weight * payout for _, weight, payout in rows) / total_w / 100.0
    return avg / cost


def allocate(groups: dict[str, list[tuple[int, int]]], probs: dict[str, float]) -> dict[int, int]:
    weights: dict[int, int] = {}
    for name, members in groups.items():
        if not members:
            continue
        budget = max(len(members), int(round(probs.get(name, 0.0) * TOTAL)))
        share, extra = divmod(budget, len(members))
        for index, (sim_id, _payout) in enumerate(members):
            weights[sim_id] = share + (1 if index < extra else 0)
    # Renormalize to TOTAL.
    current = sum(weights.values()) or 1
    scaled = {sim_id: max(1, int(weight * TOTAL / current)) for sim_id, weight in weights.items()}
    drift = TOTAL - sum(scaled.values())
    order = list(scaled)
    cursor = 0
    while drift != 0 and order:
        sim_id = order[cursor % len(order)]
        if drift > 0:
            scaled[sim_id] += 1
            drift -= 1
        elif scaled[sim_id] > 1:
            scaled[sim_id] -= 1
            drift += 1
        cursor += 1
        if cursor > len(order) * 5 and drift < 0 and all(value == 1 for value in scaled.values()):
            break
    return scaled


def ev_from_probs(means: dict[str, float], probs: dict[str, float]) -> float:
    return sum(probs[name] * means.get(name, 0.0) for name in probs)


def solve_fixed(
    groups: dict[str, list[tuple[int, int]]],
    cost: float,
    freegame_prob: float | None = None,
) -> dict[str, float]:
    """Hit the RTP by moving only the bar-fill weight. Bonus rate stays locked."""
    means = {name: mean_x([payout for _sid, payout in members]) for name, members in groups.items() if members}
    target = TARGET_RTP * cost
    base_mean = means.get("basegame", 0.0)
    pay_mean = means.get("bar_pay", base_mean)
    fg_mean = means.get("freegame", base_mean)
    p_fg = 0.0 if "freegame" not in means else float(freegame_prob or 0.0)
    p_fg = min(p_fg, 0.9)
    # ev = (1 - p_fg - p_pay) * Eb + p_pay * Ep + p_fg * Ef
    slope = pay_mean - base_mean
    if "bar_pay" in means and abs(slope) > 1e-9:
        p_pay = (target - base_mean - p_fg * (fg_mean - base_mean)) / slope
    else:
        p_pay = 0.0
    p_pay = min(0.25, max(0.0, p_pay))
    if "bar_pay" not in means:
        p_pay = 0.0
    p_base = max(0.0, 1.0 - p_pay - p_fg)
    total = p_base + p_pay + p_fg
    probs = {"basegame": p_base / total, "bar_pay": p_pay / total, "freegame": p_fg / total}
    return {name: probs[name] for name in probs if name in means}


def nudge(rows: list[tuple[int, int, int]], cost: float) -> list[tuple[int, int, int]]:
    target_sum = TARGET_RTP * cost * 100.0 * TOTAL
    weighted = [list(row) for row in rows]
    for _ in range(8):
        total_w = sum(row[1] for row in weighted)
        current = sum(row[1] * row[2] for row in weighted) * (TOTAL / total_w)
        delta = target_sum - current
        if abs(delta) < 1:
            break
        order = sorted(range(len(weighted)), key=lambda index: weighted[index][2])
        low = order[0]
        high = order[-1]
        gap = weighted[high][2] - weighted[low][2]
        if gap <= 0:
            break
        move = int(round(delta / gap))
        move = max(-(weighted[high][1] - 1), min(move, weighted[low][1] - 1))
        if move == 0:
            break
        weighted[low][1] -= move
        weighted[high][1] += move
    return [(row[0], row[1], row[2]) for row in weighted]


def main() -> None:
    GameConfig._instance = None
    config = GameConfig()
    costs = {mode.get_name(): float(mode.get_cost()) for mode in config.bet_modes}
    solved_costs: dict[str, float] = {}
    summary = {}
    for mode in costs:
        paths = lut_paths(mode)
        if not paths:
            print("missing lut", mode)
            continue
        rows = read_lut(paths[0])
        if mode in SOLVED:
            avg = mean_x([payout for _sid, _weight, payout in rows])
            cost = round(avg / TARGET_RTP, 4)
            if cost <= 0:
                cost = 0.0001
            solved_costs[mode] = cost
            equal = max(1, TOTAL // len(rows))
            # Equal weights keep the spec mix (peak 50% dead, risky 50/40/10, mystery 50/45/5).
            weighted = [(sim_id, equal, payout) for sim_id, _weight, payout in rows]
            summary[mode] = {"cost": cost, "rtp": rtp_of(weighted, cost), "books": len(rows)}
        else:
            criteria = load_criteria(mode)
            groups: dict[str, list[tuple[int, int]]] = defaultdict(list)
            for sim_id, _weight, payout in rows:
                groups[criteria.get(sim_id, "basegame")].append((sim_id, payout))
            if mode == "base":
                fg_prob = 1 / 500
            elif mode == "base_ante":
                fg_prob = 2 / 500
            else:
                # Higher hunt levels buy a higher bonus rate. Gap uses this file's own bonus.
                fg_rows = groups.get("freegame") or []
                base_rows = groups.get("basegame") or [(0, 0)]
                fg_mean = mean_x([payout for _sid, payout in fg_rows]) if fg_rows else 0.0
                base_mean = mean_x([payout for _sid, payout in base_rows])
                gap = max(fg_mean - base_mean, 1.0)
                fg_prob = max(0.0, min(0.85, (TARGET_RTP * costs[mode] - 0.5778) / gap))
            probs = solve_fixed(groups, costs[mode], fg_prob)
            allocated = allocate(groups, probs)
            weighted = [(sim_id, allocated[sim_id], payout) for sim_id, _weight, payout in rows]
            summary[mode] = {
                "cost": costs[mode],
                "rtp": rtp_of(weighted, costs[mode]),
                "books": len(rows),
                "probs": {name: round(prob, 6) for name, prob in probs.items()},
            }
        for path in paths:
            write_lut(path, weighted)
        # Ensure the publish _0 file exists even if only the base name did.
        publish_copy = PUBLISH / f"lookUpTable_{mode}_0.csv"
        if not publish_copy.exists():
            write_lut(publish_copy, weighted)
        else:
            write_lut(publish_copy, weighted)
    prices = {mode: summary[mode]["cost"] for mode in summary}
    (GAME_DIR / "mode_prices.json").write_text(json.dumps(prices, indent=2) + "\n", encoding="utf-8")
    (GAME_DIR / "reports").mkdir(exist_ok=True)
    (GAME_DIR / "reports" / "lock_rtp.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
