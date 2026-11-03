"""Shape publish weights from the books already simulated.

Each band is an equal split of a probability budget. A binary search moves
probability between two bands until the mode RTP is 96.50%. Max-win rows stay
pinned to their own probability. Payouts are never invented.
"""

from __future__ import annotations

import json
from pathlib import Path

import zstandard

from reweight_lut import (
    MODE_COSTS,
    MODE_MAX_P,
    TARGET_RTP,
    TOTAL_WEIGHT,
    read_lut,
    rtp_from_rows,
    write_lut,
)

GAME_DIR = Path(__file__).resolve().parent
PUBLISH = GAME_DIR / "library" / "publish_files"
LOOKUP = GAME_DIR / "library" / "lookup_tables"
MAX_PAY = 2_500_000

# Gamble price is the 50/45/5 formula, raised with the restored faces and tile multipliers.
GAMBLE_COST = 380.0


def _iter_books(path: Path):
    with path.open("rb") as handle:
        reader = zstandard.ZstdDecompressor().stream_reader(handle)
        buf = b""
        while True:
            chunk = reader.read(1 << 20)
            if not chunk:
                if buf.strip():
                    yield json.loads(buf)
                break
            buf += chunk
            while True:
                cut = buf.find(b"\n")
                if cut < 0:
                    break
                line = buf[:cut]
                buf = buf[cut + 1 :]
                if line.strip():
                    yield json.loads(line)


def load_book_meta(mode: str) -> tuple[dict[int, str], set[int]]:
    """Criteria per book, plus base-game spins whose progress bar fired the coin game.

    Free-spin books can also activate. Those stay in the freegame bands.
    """
    path = PUBLISH / f"books_{mode}.jsonl.zst"
    criteria: dict[int, str] = {}
    coins: set[int] = set()
    for book in _iter_books(path):
        sim_id = int(book["id"])
        crit = str(book.get("criteria") or "")
        criteria[sim_id] = crit
        if crit == "freegame":
            continue
        events = book.get("events") or []
        if any(event.get("type") == "boardActivation" for event in events):
            coins.add(sim_id)
    return criteria, coins


def load_criteria(mode: str) -> dict[int, str]:
    criteria, _coins = load_book_meta(mode)
    return criteria


def _band(xbet: float, edges: list[tuple[str, float, float]]) -> str:
    for name, lo, hi in edges:
        if lo < xbet <= hi or (lo == 0 and xbet == 0 and hi == 0):
            return name
    return "tail"


def classify(mode: str, payout: int, criteria: str, coin: bool = False) -> str:
    if payout >= MAX_PAY:
        return "cap"
    xbet = payout / 100.0
    if mode == "base":
        if criteria == "freegame":
            if 6 <= xbet <= 50:
                return "fg_low"
            if 50 < xbet <= 280:
                return "fg_high"
            return "fg_out"
        # The bar-of-5 coin game is its own band so a long cascade that never
        # fills the bar is not tied to the coin-game weight.
        if coin:
            return "coin"
        if xbet <= 0:
            return "zero"
        if xbet <= 1:
            return "small"
        if xbet <= 4:
            return "profit"
        if xbet <= 12:
            return "kicker"
        if xbet <= 60:
            return "spike"
        return "tail"
    if mode == "base_ante":
        if criteria == "freegame":
            if 6 <= xbet <= 50:
                return "fg_low"
            if 50 < xbet <= 280:
                return "fg_high"
            return "fg_out"
        if coin:
            return "coin"
        if xbet <= 0:
            return "zero"
        if xbet <= 1.4:
            return "small"
        if xbet <= 6:
            return "profit"
        if xbet <= 16:
            return "kicker"
        if xbet <= 80:
            return "spike"
        return "tail"
    if mode == "bonus_mystery":
        if criteria == "gamble_dead":
            return "dead"
        if criteria == "gamble_hear":
            if xbet <= 0:
                return "hear_zero"
            if xbet <= 100:
                return "hear_low"
            if xbet <= 200:
                return "hear_med"
            if xbet <= 360:
                return "hear_bridge"
            if xbet <= 900:
                return "hear_profit"
            return "hear_tail"
        if criteria == "gamble_madness":
            if 2200 <= xbet <= 9000:
                return "mad_body"
            return "mad_out"
        return "other"
    if mode == "feature_spin":
        if xbet <= 0:
            return "zero"
        if xbet <= 50:
            return "small"
        if xbet <= 180:
            return "profit"
        if xbet <= 420:
            return "upper"
        return "tail"
    if mode == "peak_spin":
        if xbet <= 0:
            return "zero"
        if xbet <= 5000:
            return "body"
        if xbet <= 12000:
            return "high"
        return "tail"
    if mode == "bonus_see":
        if xbet <= 0:
            return "zero"
        if xbet <= 50:
            return "low"
        if xbet <= 90:
            return "med"
        if xbet <= 140:
            return "bridge"
        if xbet <= 320:
            return "profit"
        return "tail"
    if mode == "bonus_hear":
        if xbet <= 0:
            return "zero"
        if xbet <= 100:
            return "low"
        if xbet <= 200:
            return "med"
        if xbet <= 360:
            return "bridge"
        if xbet <= 900:
            return "profit"
        return "tail"
    raise KeyError(mode)


def _natural_play_probs(mode: str, bands: dict[str, list[int]]) -> tuple[dict[str, float], str, str]:
    """Pin the hit rate, the coin game, and the bonus quota. Leave cascades alone.

    Zero stays at 80% (about a 20% hit rate). The coin band is 1/100 spins.
    Freegame books outside 6–280× stay at weight 0, and that quota is split
    across the kept freegame bands the way it was before this rebalance.
    Everything else — short wins and long tumbles that never fill the bar —
    keeps its natural share of whatever probability is left. Profit ↔ small
    is only the last nudge to 96.50%.
    """
    max_p = MODE_MAX_P[mode]
    quota = (1 / 260) if mode == "base" else (1 / 130)
    if mode == "base":
        fg_low, fg_high = 0.0023, quota - 0.0023
    else:
        # Ante's bonus quota is twice base and the cost is 1.4×. Keeping the
        # old 6–50× heavy split left the mode short, so the solver had to
        # promote a lot of small wins into profit and that shuffled tumble
        # lengths. A slightly richer 50–280× share lets the cascade bands
        # stay on their natural weights.
        fg_low, fg_high = 0.003853, quota - 0.003853
    probs = {name: 0.0 for name in bands}
    if bands.get("cap"):
        probs["cap"] = max_p
    if bands.get("zero"):
        probs["zero"] = 0.80
    if bands.get("coin"):
        probs["coin"] = 0.01
    if bands.get("fg_low"):
        probs["fg_low"] = fg_low
    if bands.get("fg_high"):
        probs["fg_high"] = fg_high
    play = [name for name in ("small", "profit", "kicker", "spike", "tail") if bands.get(name)]
    natural = {name: len(idxs) for name, idxs in bands.items()}
    play_count = sum(natural[name] for name in play) or 1
    remain = 1.0 - sum(probs.values())
    if remain < 0:
        # Pins overlap an empty play section. Shrink zero first.
        probs["zero"] = max(0.0, probs.get("zero", 0.0) + remain)
        remain = 0.0
    for name in play:
        probs[name] = remain * natural[name] / play_count
    gap = 1.0 - sum(probs.values())
    sink = "small" if bands.get("small") else (play[0] if play else "zero")
    probs[sink] = probs.get(sink, 0.0) + gap
    donor = "profit" if bands.get("profit") and probs.get("profit", 0.0) > 0 else (play[-1] if play else "zero")
    recv = "small" if bands.get("small") else donor
    return probs, donor, recv


def _probs_for(mode: str, bands: dict[str, list[int]]) -> tuple[dict[str, float], str, str]:
    """Return starting probabilities plus the donor and receiver used to hit RTP."""
    max_p = MODE_MAX_P[mode]
    probs = {name: 0.0 for name in bands}
    if bands.get("cap"):
        probs["cap"] = max_p
    if mode in ("base", "base_ante"):
        return _natural_play_probs(mode, bands)
    elif mode == "feature_spin":
        probs.update({"zero": 0.56, "small": 0.18, "profit": 0.18, "upper": 0.08})
        donor, recv = "small", "upper"
    elif mode == "peak_spin":
        probs.update({"zero": 0.70, "body": 0.205, "high": 0.08, "tail": 0.015 - max_p})
        donor, recv = "high", "body"
    elif mode == "bonus_see":
        probs.update({"zero": 0.02, "low": 0.24, "med": 0.28, "bridge": 0.23, "profit": 0.20, "tail": 0.03 - max_p})
        donor, recv = "profit", "med"
    elif mode == "bonus_hear":
        probs.update({"zero": 0.01, "low": 0.22, "med": 0.36, "bridge": 0.23, "profit": 0.16, "tail": 0.02 - max_p})
        donor, recv = "profit", "bridge"
    elif mode == "bonus_mystery":
        hear_p = 0.45
        mad_p = 0.05
        dead_p = 0.50 - max_p
        probs.update(
            {
                "dead": dead_p,
                "hear_low": hear_p * 0.22,
                "hear_med": hear_p * 0.36,
                "hear_bridge": hear_p * 0.23,
                "hear_profit": hear_p * 0.16,
                "hear_tail": hear_p * 0.03,
                "mad_body": mad_p,
            }
        )
        donor, recv = "hear_profit", "hear_med"
    else:
        raise KeyError(mode)
    total = sum(probs.values())
    if abs(total - 1.0) > 1e-4:
        sink = "small" if "small" in probs else recv
        probs[sink] = probs.get(sink, 0.0) + (1.0 - total)
    return probs, donor, recv


def _drop_empty(bands: dict[str, list[int]], probs: dict[str, float], recv: str) -> None:
    for name, prob in list(probs.items()):
        if prob <= 0 or bands.get(name):
            continue
        sink = recv if bands.get(recv) else next((key for key, idxs in bands.items() if idxs), name)
        if sink == name:
            continue
        probs[sink] = probs.get(sink, 0.0) + prob
        probs[name] = 0.0


def _weights(rows: list[tuple[int, int, int]], bands: dict[str, list[int]], probs: dict[str, float]):
    raw = [0.0] * len(rows)
    for name, idxs in bands.items():
        prob = probs.get(name, 0.0)
        if not idxs or prob <= 0:
            continue
        share = prob / len(idxs)
        for index in idxs:
            raw[index] = share
    total = sum(raw) or 1.0
    exact = [value / total * TOTAL_WEIGHT for value in raw]
    weights = [int(value) for value in exact]
    short = TOTAL_WEIGHT - sum(weights)
    if short > 0:
        order = sorted(range(len(exact)), key=lambda i: exact[i] - weights[i], reverse=True)
        whole, rest = divmod(short, len(order))
        if whole:
            for index in order:
                weights[index] += whole
        for index in order[:rest]:
            weights[index] += 1
    elif short < 0:
        order = sorted(range(len(weights)), key=lambda i: weights[i], reverse=True)
        for index in order:
            if short == 0:
                break
            take = min(weights[index], -short)
            weights[index] -= take
            short += take
    return [(rows[i][0], weights[i], rows[i][2]) for i in range(len(rows))]


def _apply(probs: dict[str, float], donor: str, recv: str, delta: float) -> dict[str, float]:
    shifted = dict(probs)
    shifted[donor] = probs.get(donor, 0.0) - delta
    shifted[recv] = probs.get(recv, 0.0) + delta
    return shifted


def _solve(rows, bands, probs, donor, recv, cost):
    """Move probability between two bands until RTP is 96.50%.

    The search first checks which direction moves RTP toward the target, then
    binary-searches that direction. ``delta`` always takes weight from ``donor``.
    """

    def scored(donor_name: str, recv_name: str, delta: float):
        shifted = _apply(probs, donor_name, recv_name, delta)
        weighted = _weights(rows, bands, shifted)
        return rtp_from_rows(weighted, cost), weighted, shifted

    start_rtp, start_rows, _ = scored(donor, recv, 0.0)
    step = min(0.005, max(probs.get(donor, 0.0), 0.0))
    probe = scored(donor, recv, step)[0] if step > 0 else start_rtp
    toward = (start_rtp > TARGET_RTP and probe < start_rtp) or (start_rtp < TARGET_RTP and probe > start_rtp)
    if not toward:
        donor, recv = recv, donor
    lo = 0.0
    hi = max(0.0, probs.get(donor, 0.0))
    # Confirm the chosen direction is monotonic toward the target as delta grows.
    confirm = scored(donor, recv, min(0.005, hi))[0] if hi > 0 else start_rtp
    increasing = confirm > start_rtp
    best_rows = start_rows
    best_gap = abs(start_rtp - TARGET_RTP)
    best_probs = dict(probs)
    for _ in range(32):
        mid = (lo + hi) / 2.0
        rtp, weighted, shifted = scored(donor, recv, mid)
        if abs(rtp - TARGET_RTP) < best_gap:
            best_rows, best_gap, best_probs = weighted, abs(rtp - TARGET_RTP), shifted
        if increasing:
            if rtp < TARGET_RTP:
                lo = mid
            else:
                hi = mid
        elif rtp > TARGET_RTP:
            lo = mid
        else:
            hi = mid
    return best_rows, best_probs


def fit_rows(
    mode: str,
    rows: list[tuple[int, int, int]],
    criteria: dict[int, str],
    coin_ids: set[int] | None = None,
):
    cost = GAMBLE_COST if mode == "bonus_mystery" else MODE_COSTS[mode]
    coins = coin_ids or set()
    bands: dict[str, list[int]] = {}
    for index, (sim_id, _, payout) in enumerate(rows):
        name = classify(mode, payout, criteria.get(sim_id, ""), sim_id in coins)
        bands.setdefault(name, []).append(index)
    probs, donor, recv = _probs_for(mode, bands)
    _drop_empty(bands, probs, recv)
    weighted, used = _solve(rows, bands, probs, donor, recv, cost)
    return weighted, bands, used, cost


def mode_stats(weighted, cost: float) -> dict:
    import math

    total_w = sum(weight for _, weight, _ in weighted if weight > 0)
    items = []
    for _, weight, payout in weighted:
        if weight <= 0:
            continue
        x = payout / 100.0 / cost
        items.append((x, weight))
    items.sort()
    origin = loss = zero = profit = 0.0
    second = 0.0
    for x, weight in items:
        p = weight / total_w
        origin += p * x
        second += p * x * x
        if x == 0:
            zero += p
        if x < 1:
            loss += p
        if x > 1:
            profit += p
    acc = 0
    half = (total_w + 1) // 2
    median = items[-1][0]
    for x, weight in items:
        acc += weight
        if acc >= half:
            median = x
            break

    def top(mass: float) -> float:
        left = mass
        held = 0.0
        for x, weight in reversed(items):
            if left <= 0:
                break
            take = min(left, weight / total_w)
            held += take * x
            left -= take
        return held / origin if origin else 0.0

    max_x, max_w = items[-1]
    return {
        "rtp": origin,
        "zero": zero,
        "loss": loss,
        "profit": profit,
        "median": median,
        "sd": math.sqrt(max(0.0, second - origin * origin)),
        "max_p": max_w / total_w,
        "max_share": (max_w / total_w) * max_x / origin if origin else 0.0,
        "top1": top(0.01),
        "top01": top(0.001),
    }


def fit_mode(mode: str, criteria: dict[int, str] | None = None, coin_ids: set[int] | None = None):
    rows = read_lut(LOOKUP / f"lookUpTable_{mode}.csv")
    if criteria is None or coin_ids is None:
        loaded_criteria, loaded_coins = load_book_meta(mode)
        if criteria is None:
            criteria = loaded_criteria
        if coin_ids is None:
            coin_ids = loaded_coins
    weighted, bands, probs, cost = fit_rows(mode, rows, criteria, coin_ids)
    counts = {name: len(idxs) for name, idxs in sorted(bands.items())}
    return weighted, mode_stats(weighted, cost), counts, probs, cost


def write_mode(mode: str) -> dict:
    weighted, stats, counts, probs, cost = fit_mode(mode)
    write_lut(PUBLISH / f"lookUpTable_{mode}_0.csv", weighted)
    return {"mode": mode, "cost": cost, "rtp": stats["rtp"], "stats": stats, "counts": counts}


if __name__ == "__main__":
    import sys

    write = "--write" in sys.argv
    modes = [arg for arg in sys.argv[1:] if not arg.startswith("--")] or list(MODE_COSTS)
    for mode in modes:
        if write:
            item = write_mode(mode)
            stats = item["stats"]
            print(f"\n== wrote {mode} cost {item['cost']}", flush=True)
        else:
            _, stats, counts, probs, cost = fit_mode(mode)
            print(f"\n== {mode} cost {cost}", flush=True)
            print("  bands", counts, flush=True)
            print("  probs", {k: round(v, 5) for k, v in probs.items() if v > 0}, flush=True)
        for key, value in stats.items():
            print(f"  {key:10} {value:.6f}")
