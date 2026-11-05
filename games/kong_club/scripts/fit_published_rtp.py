"""Publish lookup weights for the current 500-book libraries.

Base and Ante keep bonus rates of 1/500 and 1/250. Their coin-bar rate is
solved inside 1/300–1/600. Hunt prices and scatter rates stay put unless the
sample cannot reach 96.3% at those odds. Buys and Trifecta keep their prices
(Trifecta 1,000x, 50% dead, live half averaging 1,926x). Feature Spin price is
re-solved into 50–75x from the book mean.
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
FIXED = {"base": 1.0, "base_ante": 1.4, **HUNT_COSTS, "peak_spin": 1000.0}
FEATURE_PRICE_MIN = 50.0
FEATURE_PRICE_MAX = 75.0


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
    # Don't fill the base bar more often than about 1 in 300. Rarer is allowed
    # when near-miss clusters carry more of the return.
    if cost in (1.0, 1.4):
        p_pay = min(1 / 300, max(0.0, p_pay))
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


def nudge_toward(
    rows: list[tuple[int, int, int]],
    cost: float,
    protected: set[int] | None = None,
    pool: set[int] | None = None,
) -> list[tuple[int, int, int]]:
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
        candidates = [
            index
            for index, row in enumerate(weighted)
            if row[0] not in protected and (pool is None or row[0] in pool)
        ]
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


BUY_COSTS = {"bonus_see": 100.0, "bonus_hear": 300.0, "bonus_pick": 330.0, "bonus_risky": 500.0}
BUY_MIX = {
    "bonus_pick": {"pick_see": 0.50, "pick_hear": 0.45, "pick_speak": 0.05},
    "bonus_risky": {"risky_dead": 0.50, "risky_hear": 0.40, "risky_speak": 0.10},
}


def is_upgrade(book: dict) -> bool:
    return any(
        ev.get("type") == "kongClubMode" and ev.get("state") == "upgrade_bonus_speak"
        for ev in book.get("events") or []
    )


def weighted_median(pays: list[float], weights: list[float]) -> float:
    order = sorted(range(len(pays)), key=lambda index: (pays[index], index))
    total = sum(weights) or 1.0
    acc = 0.0
    for index in order:
        acc += weights[index]
        if acc >= total * 0.5:
            return pays[index]
    return pays[order[-1]]


def see_weights(pays: list[float]) -> list[float]:
    """Median near 45x and mean on 96.3x. The top is trimmed, the middle is lifted."""
    best: tuple | None = None
    for low_share in (0.42, 0.45, 0.47, 0.49):
        for mid_lo, mid_hi in ((38, 48), (40, 50), (40, 52), (42, 55)):
            mid_idx = [i for i, payout in enumerate(pays) if mid_lo <= payout <= mid_hi]
            low_idx = [i for i, payout in enumerate(pays) if payout < mid_lo]
            high_idx = [i for i, payout in enumerate(pays) if payout > mid_hi]
            if not mid_idx or not high_idx or not low_idx:
                continue
            low_mean = mean([pays[i] for i in low_idx])
            mid_mean = mean([pays[i] for i in mid_idx])
            # Mean identity: low_share * L + mid_share * M + high_share * H = 96.3
            for mid_share in (0.04, 0.06, 0.08, 0.10, 0.12):
                high_share = 1.0 - low_share - mid_share
                if high_share <= 0.05:
                    continue
                high_target = (96.3 - low_share * low_mean - mid_share * mid_mean) / high_share
                high_pays = [pays[i] for i in high_idx]
                if not (min(high_pays) < high_target < max(high_pays)):
                    continue
                high_raw = gamma_weights(high_pays, high_target)
                raw = [0.0] * len(pays)
                for index in low_idx:
                    raw[index] = low_share / len(low_idx)
                for index in mid_idx:
                    raw[index] = mid_share / len(mid_idx)
                for weight, index in zip(high_raw, high_idx):
                    raw[index] = weight
                # Renormalize the high piece to high_share.
                high_sum = sum(raw[index] for index in high_idx) or 1.0
                for index in high_idx:
                    raw[index] = raw[index] / high_sum * high_share
                med = weighted_median(pays, raw)
                avg = sum(payout * weight for payout, weight in zip(pays, raw))
                med_pen = 0.0 if 40 <= med <= 50 else min(abs(med - 40), abs(med - 50))
                err = abs(avg - 96.3) + med_pen * 8
                if best is None or err < best[0]:
                    best = (err, raw, med, avg)
    if best is None:
        return [1.0] * len(pays)
    return best[1]


def attach(members: list[tuple[int, int]], raw: list[float], budget: int) -> list[tuple[int, int, int]]:
    if not members:
        return []
    weights = integers(raw, max(budget, len(members)))
    return [
        (sim_id, weight, payout)
        for (sim_id, payout), weight in zip(members, weights)
    ]


def fit_group_mean(members: list[tuple[int, int]], target: float, budget: int) -> list[tuple[int, int, int]]:
    pays = [payout / 100.0 for _sid, payout in members]
    if not pays:
        return []
    lo, hi = min(pays), max(pays)
    goal = min(max(target, lo + 1e-6), hi - 1e-6) if hi > lo else lo
    raw = gamma_weights(pays, goal) if hi > lo else [1.0] * len(pays)
    return attach(members, raw, budget)


def fit_buy(mode: str, books: list[dict], cost: float) -> tuple[list[tuple[int, int, int]], dict[str, float]]:
    """Hold the published price, the outcome mix, and the Hear→Speak rate.

    Upgrade books and direct-Speak books stay equally weighted, so those path
    averages stay at the book means. Other books are reshaped to the price.
    """
    target = TARGET * cost
    upgrades = {int(book["id"]) for book in books if is_upgrade(book)}
    if mode == "bonus_see":
        ordered = [(int(book["id"]), int(book["payoutMultiplier"])) for book in books]
        pays = [payout / 100.0 for _sid, payout in ordered]
        raw = see_weights(pays)
        rows = attach(ordered, raw, TOTAL)
        rows = renormalize(rows)
        band = {sid for sid, payout in ordered if 35 <= payout / 100.0 <= 60}
        rows = nudge_toward(rows, cost, protected=band)
        by_id = {sid: weight for sid, weight, _pay in rows}
        med = weighted_median(pays, [by_id[sid] for sid, _pay in ordered])
        print(f"  see weighted median {med:.2f}x")
        return rows, {"bonus_see": 1.0, "median": round(med, 2)}

    mix = BUY_MIX.get(mode)
    grouped: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for book in books:
        grouped[str(book.get("criteria") or mode)].append((int(book["id"]), int(book["payoutMultiplier"])))
    if mix is None:
        mix = {mode: 1.0}

    # (members, budget, flexible)
    pieces: list[tuple[list[tuple[int, int]], int, bool]] = []
    probs: dict[str, float] = {}
    for name, share in mix.items():
        members = grouped.get(name, [])
        probs[name] = share
        if not members:
            continue
        budget = int(round(share * TOTAL))
        pinned = name.endswith("speak") or name.endswith("dead")
        if pinned:
            pieces.append((members, budget, False))
            continue
        upgraded = [row for row in members if row[0] in upgrades]
        rest = [row for row in members if row[0] not in upgrades]
        rate = len(upgraded) / len(members) if members else 0.0
        up_budget = int(round(budget * rate))
        if upgraded:
            pieces.append((upgraded, max(up_budget, len(upgraded)), False))
        rest_budget = max(budget - max(up_budget, 0), len(rest) if rest else 0)
        if rest:
            pieces.append((rest, rest_budget, True))
        if name == "bonus_hear" or name.endswith("hear"):
            probs["upgrade_rate"] = round(rate if mix.get(name, 1) == 1 and len(mix) == 1 else share * rate, 6)

    def piece_mean(members: list[tuple[int, int]], gamma: float, flexible: bool) -> float:
        pays = [payout / 100.0 for _sid, payout in members]
        if not flexible or len(set(pays)) <= 1:
            return mean(pays)
        raw = [(payout + 0.05) ** (-gamma) for payout in pays]
        return sum(weight * payout for weight, payout in zip(raw, pays)) / sum(raw)

    def mixture(gamma: float) -> float:
        total_w = sum(budget for _m, budget, _f in pieces) or 1
        return sum(budget * piece_mean(members, gamma, flexible) for members, budget, flexible in pieces) / total_w

    lo, hi = -3.0, 8.0
    for _ in range(48):
        gamma = (lo + hi) / 2.0
        if mixture(gamma) > target:
            lo = gamma
        else:
            hi = gamma
    gamma = (lo + hi) / 2.0
    rows: list[tuple[int, int, int]] = []
    flex_ids: set[int] = set()
    widest: tuple[float, set[int]] = (0.0, set())
    for members, budget, flexible in pieces:
        pays = [payout / 100.0 for _sid, payout in members]
        raw = [(payout + 0.05) ** (-gamma) for payout in pays] if flexible else [1.0] * len(members)
        rows += attach(members, raw, budget)
        if flexible:
            ids = {sid for sid, _p in members}
            flex_ids |= ids
            span = (max(pays) - min(pays)) if pays else 0.0
            if span > widest[0]:
                widest = (span, ids)
    rows = renormalize(rows)
    rows = nudge_toward(rows, cost, protected=upgrades, pool=widest[1] or flex_ids)
    return rows, probs


# Certified scatter rates. Hunt 5 is a clear step above Hunt 4. The freegame
# books are reweighted so each price still returns 96.3%.
HUNT_SCATTER_RATE = {
    "hunt_2": 0.09,
    "hunt_3": 0.13,
    "hunt_4": 0.18,
    "hunt_5": 0.45,
}


def fit_hunt(groups, cost: float, rate: float, bar_prob: float):
    """Hold a scatter rate and reshape the bonus books to the locked price."""
    base_rows = groups.get("basegame", [])
    bar_rows = groups.get("bar_pay", [])
    fg_rows = groups.get("freegame", [])
    eb = mean([payout / 100.0 for _sid, payout in base_rows]) if base_rows else 0.0
    ep = mean([payout / 100.0 for _sid, payout in bar_rows]) if bar_rows else eb
    fg_pays = [payout / 100.0 for _sid, payout in fg_rows]
    target = TARGET * cost
    pb = bar_prob if bar_rows else 0.0
    # Shrink the rate if the bonus sample cannot reach the conditional mean.
    chosen = rate
    for _ in range(12):
        gap = max(chosen, 1e-6)
        ef = (target - (1.0 - chosen - pb) * eb - pb * ep) / gap
        if fg_pays and min(fg_pays) < ef < max(fg_pays):
            break
        chosen = max(0.02, chosen * 0.85)
    else:
        ef = mean(fg_pays) if fg_pays else 0.0
    p_base = max(0.0, 1.0 - chosen - pb)
    rows = fit_group_mean(fg_rows, ef, int(round(chosen * TOTAL)))
    rows += attach(bar_rows, [1.0] * len(bar_rows), int(round(pb * TOTAL)))
    rows += attach(base_rows, [1.0] * len(base_rows), int(round(p_base * TOTAL)))
    rows = renormalize(rows)
    rows = nudge_toward(rows, cost, pool={sid for sid, _p in fg_rows})
    probs = {"freegame": chosen, "bar_pay": pb, "basegame": p_base}
    return rows, probs


def fit_hunt5(groups, cost: float, hunt4_rate: float, base_bar: float):
    """Scatter rate clearly above Hunt 4. Bar weight and the bonus tail pay for it."""
    base_rows = groups.get("basegame", [])
    bar_rows = groups.get("bar_pay", [])
    fg_rows = groups.get("freegame", [])
    eb = mean([payout / 100.0 for _sid, payout in base_rows])
    ep = mean([payout / 100.0 for _sid, payout in bar_rows]) if bar_rows else eb
    fg_pays = [payout / 100.0 for _sid, payout in fg_rows]
    fg_pays_sorted = sorted(fg_pays)
    floor = fg_pays_sorted[max(0, len(fg_pays_sorted) // 8)] if fg_pays_sorted else 0.0
    ceiling = fg_pays_sorted[min(len(fg_pays_sorted) - 1, (len(fg_pays_sorted) * 7) // 8)] if fg_pays_sorted else 0.0
    target = TARGET * cost
    desired = max(2.75 * hunt4_rate, hunt4_rate + 0.08, 0.16)
    pb = base_bar if bar_rows else 0.0

    def needed(pf: float, bar: float) -> float:
        gap = max(pf, 1e-9)
        return (target - (1.0 - pf - bar) * eb - bar * ep) / gap

    ef = needed(desired, pb)
    if ef < floor:
        pb = 0.0
        ef = needed(desired, pb)
    if ef < floor or ef > ceiling:
        # Highest scatter rate whose conditional mean still sits in the sample.
        pb = 0.0
        ef = min(max(mean(fg_pays), floor), ceiling)
        desired = (target - eb) / max(ef - eb, 1e-6)
        desired = min(0.45, max(hunt4_rate, desired))
        ef = needed(desired, pb)
        ef = min(max(ef, floor), ceiling)
    p_base = max(0.0, 1.0 - desired - pb)
    rows = fit_group_mean(fg_rows, ef, int(round(desired * TOTAL)))
    rows += attach(bar_rows, [1.0] * len(bar_rows), int(round(pb * TOTAL)))
    rows += attach(base_rows, [1.0] * len(base_rows), int(round(p_base * TOTAL)))
    rows = renormalize(rows)
    rows = nudge_toward(rows, cost, pool={sid for sid, _p in fg_rows})
    probs = {"freegame": desired, "bar_pay": pb, "basegame": p_base}
    return rows, probs


def solve_feature_price(pays: list[float]) -> float:
    """Half-step price inside 50–75x whose 96.3% target the sample can hit."""
    natural = mean(pays) / TARGET
    if natural < FEATURE_PRICE_MIN:
        cost = FEATURE_PRICE_MIN
    elif natural > FEATURE_PRICE_MAX:
        cost = FEATURE_PRICE_MAX
    else:
        cost = round(natural * 2.0) / 2.0
        cost = min(FEATURE_PRICE_MAX, max(FEATURE_PRICE_MIN, cost))
    if min(pays) < cost * TARGET < max(pays):
        return cost
    for edge in (FEATURE_PRICE_MAX, FEATURE_PRICE_MIN):
        if min(pays) < edge * TARGET < max(pays):
            return edge
    raise SystemExit(
        "feature_spin sample cannot price inside 50–75x "
        f"(mean {mean(pays):.2f}x, range {min(pays):.2f}–{max(pays):.2f})"
    )


def main() -> None:
    prices = json.loads((GAME / "mode_prices.json").read_text(encoding="utf-8"))
    modes = list(prices)
    # Base bar rate is solved first. Ante solves its own. Hunt 2–4 hold the base
    # bar rate. Hunt 5's scatter rate is set above Hunt 4, and its bar rate gives.
    base_books = read_books("base")
    base_groups = group_rows(base_books)
    base_probs = solve_bar(base_groups, 1.0, 1 / 500)
    base_bar = base_probs["bar_pay"]
    summary = {}
    hunt4_rate = 0.0
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
            rows, probs = fit_hunt(groups, cost, HUNT_SCATTER_RATE[mode], base_bar)
            if mode == "hunt_4":
                hunt4_rate = probs["freegame"]
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
            members = groups.get("run") or [
                (int(book["id"]), int(book["payoutMultiplier"])) for book in books
            ]
            pays = [payout / 100.0 for _sid, payout in members]
            cost = solve_feature_price(pays)
            raw = gamma_weights(pays, cost * TARGET)
            weights = integers(raw, TOTAL)
            rows = [(sim_id, weight, payout) for (sim_id, payout), weight in zip(members, weights)]
            rows = nudge_toward(rows, cost)
            probs = {"run": 1.0}
        else:
            cost = BUY_COSTS[mode]
            rows, probs = fit_buy(mode, books, cost)
        prices[mode] = cost
        write_lut(mode, rows)
        summary[mode] = {"cost": cost, "rtp": rtp(rows, cost), "probs": {k: round(v, 6) for k, v in probs.items()}}
        print(f"{mode:14} cost {cost:10.4f}  RTP {summary[mode]['rtp']*100:.4f}%  {summary[mode]['probs']}")
    (GAME / "mode_prices.json").write_text(json.dumps(prices, indent=2) + "\n", encoding="utf-8")
    (GAME / "reports" / "lock_rtp.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    index_path = PUBLISH / "index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        for mode in index.get("modes", []):
            if mode.get("name") in prices:
                mode["cost"] = prices[mode["name"]]
        index_path.write_text(json.dumps(index, indent=4) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
