"""Publish lookup weights for the current 500-book libraries.

Base and Ante keep bonus rates of 1/500 and 1/250. Their coin-bar rate is
solved inside 1/300–1/600. Hunt prices stay put. Buys, Feature, and Trifecta
use the prices in mode_prices.json (Feature 75x, Trifecta 1,000x). Trifecta
keeps a 50% dead rate and a live half averaging 1,926x.
"""

from __future__ import annotations

import io
import json
from collections import defaultdict
from pathlib import Path

import zstandard

GAME = Path(__file__).resolve().parents[1]
PUBLISH = GAME / "library" / "publish_files"
TOTAL = 10_000_000_000
TARGET = 0.963
LIVE_TARGET = 1926.0  # 0.5 * 1926 / 1000 = 0.963
HUNT_COSTS = {"hunt_2": 5.0, "hunt_3": 6.0, "hunt_4": 10.0, "hunt_5": 25.0}
FIXED = {"base": 1.0, "base_ante": 1.4, **HUNT_COSTS, "feature_spin": 75.0, "peak_spin": 1000.0}


def read_books(mode: str) -> list[dict]:
    path = PUBLISH / f"books_{mode}.jsonl.zst"
    books = []
    with path.open("rb") as handle:
        text = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(handle), encoding="utf-8")
        for line in text:
            if line.strip():
                books.append(json.loads(line))
    return books


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def gamma_weights(payouts: list[float], target: float) -> list[float]:
    """Positive weights whose mean equals target, when target sits inside the sample."""
    lo, hi = -2.0, 8.0
    for _ in range(60):
        gamma = (lo + hi) / 2.0
        weights = [(payout + 0.05) ** (-gamma) for payout in payouts]
        avg = sum(weight * payout for weight, payout in zip(weights, payouts)) / sum(weights)
        if avg > target:
            lo = gamma
        else:
            hi = gamma
    gamma = (lo + hi) / 2.0
    return [(payout + 0.05) ** (-gamma) for payout in payouts]


def integers(raw: list[float], budget: int) -> list[int]:
    budget = max(budget, len(raw))
    total = sum(raw) or 1.0
    exact = [weight / total * budget for weight in raw]
    weights = [max(1, int(weight)) for weight in exact]
    drift = budget - sum(weights)
    order = sorted(range(len(exact)), key=lambda index: exact[index] - int(exact[index]), reverse=True)
    cursor = 0
    while drift != 0 and order:
        index = order[cursor % len(order)]
        if drift > 0:
            weights[index] += 1
            drift -= 1
        elif weights[index] > 1:
            weights[index] -= 1
            drift += 1
        else:
            cursor += 1
            if cursor > len(order) * 3:
                break
            continue
        cursor += 1
    return weights


def write_lut(mode: str, rows: list[tuple[int, int, int]]) -> None:
    text = "".join(f"{sim_id},{weight},{payout}\n" for sim_id, weight, payout in rows)
    for folder in (PUBLISH, GAME / "library" / "lookup_tables"):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"lookUpTable_{mode}_0.csv").write_text(text, encoding="utf-8")
        plain = folder / f"lookUpTable_{mode}.csv"
        if plain.exists() or folder == PUBLISH:
            plain.write_text(text, encoding="utf-8")


def group_rows(books: list[dict]) -> dict[str, list[tuple[int, int]]]:
    groups: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for book in books:
        groups[str(book.get("criteria") or "basegame")].append(
            (int(book["id"]), int(book["payoutMultiplier"]))
        )
    return groups


def ev(groups: dict[str, list[tuple[int, int]]], probs: dict[str, float]) -> float:
    total = 0.0
    for name, members in groups.items():
        if not members or name not in probs:
            continue
        total += probs[name] * mean([payout / 100.0 for _sid, payout in members])
    return total


def solve_bar(groups, cost: float, freegame_prob: float) -> dict[str, float]:
    means = {name: mean([payout / 100.0 for _sid, payout in members]) for name, members in groups.items()}
    base_mean = means.get("basegame", 0.0)
    pay_mean = means.get("bar_pay", base_mean)
    fg_mean = means.get("freegame", base_mean)
    target = TARGET * cost
    slope = pay_mean - base_mean
    if abs(slope) < 1e-9 or "bar_pay" not in means:
        p_pay = 0.0
    else:
        p_pay = (target - base_mean - freegame_prob * (fg_mean - base_mean)) / slope
    # Base and Ante are asked to fill the bar every 300–600 spins.
    if cost in (1.0, 1.4):
        p_pay = min(1 / 300, max(1 / 600, p_pay))
    else:
        p_pay = min(0.2, max(0.0, p_pay))
    p_fg = freegame_prob if "freegame" in means else 0.0
    p_base = max(0.0, 1.0 - p_pay - p_fg)
    total = p_base + p_pay + p_fg or 1.0
    return {
        "basegame": p_base / total,
        "bar_pay": p_pay / total,
        "freegame": p_fg / total,
    }


def hunt_freegame_prob(groups, cost: float, bar_prob: float) -> float:
    means = {name: mean([payout / 100.0 for _sid, payout in members]) for name, members in groups.items()}
    base_mean = means.get("basegame", 0.0)
    pay_mean = means.get("bar_pay", base_mean)
    fg_mean = means.get("freegame", base_mean + 1.0)
    target = TARGET * cost
    # Hold the base bar rate, solve the bonus rate that hits the locked price.
    gap = fg_mean - base_mean
    if abs(gap) < 1e-6:
        return 0.0
    # ev = (1 - pf - pb)*Eb + pb*Ep + pf*Ef
    p_fg = (target - base_mean - bar_prob * (pay_mean - base_mean)) / gap
    return min(0.85, max(0.0, p_fg))


def rows_from_probs(groups, probs: dict[str, float]) -> list[tuple[int, int, int]]:
    weighted: list[tuple[int, int, int]] = []
    for name, members in groups.items():
        if not members:
            continue
        budget = int(round(probs.get(name, 0.0) * TOTAL))
        budget = max(budget, len(members))
        share = integers([1.0] * len(members), budget)
        for (sim_id, payout), weight in zip(members, share):
            weighted.append((sim_id, weight, payout))
    return renormalize(weighted)


def renormalize(rows: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    current = sum(weight for _sid, weight, _pay in rows) or 1
    scaled = [(sim_id, max(1, int(weight * TOTAL / current)), payout) for sim_id, weight, payout in rows]
    drift = TOTAL - sum(weight for _sid, weight, _pay in scaled)
    cursor = 0
    scaled_l = [list(row) for row in scaled]
    while drift != 0 and scaled_l:
        index = cursor % len(scaled_l)
        if drift > 0:
            scaled_l[index][1] += 1
            drift -= 1
        elif scaled_l[index][1] > 1:
            scaled_l[index][1] -= 1
            drift += 1
        cursor += 1
        if cursor > len(scaled_l) * 4:
            break
    return [(row[0], row[1], row[2]) for row in scaled_l]


def nudge_toward(rows: list[tuple[int, int, int]], cost: float, protected: set[int] | None = None) -> list[tuple[int, int, int]]:
    """Move weight between two unprotected rows until the RTP matches."""
    protected = protected or set()
    target_sum = TARGET * cost * 100.0 * TOTAL
    weighted = [list(row) for row in rows]
    for _ in range(12):
        total_w = sum(row[1] for row in weighted) or 1
        current = sum(row[1] * row[2] for row in weighted) * (TOTAL / total_w)
        delta = target_sum - current
        if abs(delta) < 1:
            break
        candidates = [index for index, row in enumerate(weighted) if row[0] not in protected]
        if len(candidates) < 2:
            break
        candidates.sort(key=lambda index: weighted[index][2])
        low, high = candidates[0], candidates[-1]
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


def rtp(rows: list[tuple[int, int, int]], cost: float) -> float:
    total_w = sum(weight for _sid, weight, _pay in rows) or 1
    return sum(weight * payout for _sid, weight, payout in rows) / total_w / 100.0 / cost


def main() -> None:
    prices = json.loads((GAME / "mode_prices.json").read_text(encoding="utf-8"))
    modes = list(prices)
    # Base bar rate is solved first and reused so Ante/Hunt share the same fill
    # when that still hits their RTP. Ante may need its own fill rate.
    base_books = read_books("base")
    base_groups = group_rows(base_books)
    base_probs = solve_bar(base_groups, 1.0, 1 / 500)
    base_bar = base_probs["bar_pay"]
    summary = {}
    for mode in modes:
        books = read_books(mode)
        groups = group_rows(books)
        if mode == "base":
            probs = base_probs
            rows = rows_from_probs(groups, probs)
            rows = nudge_toward(rows, 1.0)
            cost = 1.0
        elif mode == "base_ante":
            probs = solve_bar(groups, 1.4, 2 / 500)
            rows = rows_from_probs(groups, probs)
            rows = nudge_toward(rows, 1.4)
            cost = 1.4
        elif mode in HUNT_COSTS:
            cost = HUNT_COSTS[mode]
            p_fg = hunt_freegame_prob(groups, cost, base_bar)
            probs = {
                "freegame": p_fg,
                "bar_pay": base_bar if "bar_pay" in groups else 0.0,
            }
            probs["basegame"] = max(0.0, 1.0 - probs["freegame"] - probs["bar_pay"])
            total = sum(probs.values()) or 1.0
            probs = {name: value / total for name, value in probs.items()}
            rows = rows_from_probs(groups, probs)
            rows = nudge_toward(rows, cost)
        elif mode == "peak_spin":
            cost = 1000.0
            dead = groups.get("dead_juicy", [])
            live = groups.get("live", [])
            live_pays = [payout / 100.0 for _sid, payout in live]
            raw = gamma_weights(live_pays, LIVE_TARGET)
            dead_w = integers([1.0] * len(dead), TOTAL // 2)
            live_w = integers(raw, TOTAL - TOTAL // 2)
            rows = [(sim_id, weight, payout) for (sim_id, payout), weight in zip(dead, dead_w)]
            rows += [(sim_id, weight, payout) for (sim_id, payout), weight in zip(live, live_w)]
            # Nudge only inside the live half so the dead rate stays 50%.
            rows = nudge_toward(rows, cost, protected={sim_id for sim_id, _pay in dead})
            probs = {"dead_juicy": 0.5, "live": 0.5}
        elif mode == "feature_spin":
            cost = 75.0
            pays = [payout / 100.0 for _sid, payout in groups["run"]]
            raw = gamma_weights(pays, cost * TARGET)
            weights = integers(raw, TOTAL)
            rows = [(sim_id, weight, payout) for (sim_id, payout), weight in zip(groups["run"], weights)]
            rows = nudge_toward(rows, cost)
            probs = {"run": 1.0}
        else:
            pays = [book["payoutMultiplier"] / 100.0 for book in books]
            cost = round(mean(pays) / TARGET, 4)
            share = max(1, TOTAL // len(books))
            rows = [(int(book["id"]), share, int(book["payoutMultiplier"])) for book in books]
            rows = renormalize(rows)
            probs = {name: len(members) / len(books) for name, members in groups.items()}
        prices[mode] = cost
        write_lut(mode, rows)
        summary[mode] = {"cost": cost, "rtp": rtp(rows, cost), "probs": {k: round(v, 6) for k, v in probs.items()}}
        print(f"{mode:14} cost {cost:10.4f}  RTP {summary[mode]['rtp']*100:.4f}%  {summary[mode]['probs']}")
    (GAME / "mode_prices.json").write_text(json.dumps(prices, indent=2) + "\n", encoding="utf-8")
    (GAME / "reports" / "lock_rtp.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
