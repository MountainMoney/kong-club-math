"""Retarget publish LUT weights to 96.50% RTP while preserving book/LUT payout parity."""

from __future__ import annotations

import json
import math
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent
PUBLISH = GAME_DIR / "library" / "publish_files"
LOOKUP = GAME_DIR / "library" / "lookup_tables"

MODE_COSTS = {
    "base": 1.0,
    "base_ante": 1.4,
    "feature_spin": 65.0,
    "peak_spin": 1400.0,
    "bonus_see": 115.0,
    "bonus_hear": 250.0,
    "bonus_gamble": 380.0,
}

TARGET_RTP = 0.965
MODE_TARGET_RTP = {mode: TARGET_RTP for mode in MODE_COSTS}
# LUT payouts are in bet-hundredths. 25,000× = 2,500,000.
MAX_WIN_PAYOUT = 2_500_000
PAYOUT_5K = 500_000
TOTAL_WEIGHT = 10_000_000_000
MAX_TAIL_RTP_SHARE_5K = 0.010
MAX_TAIL_RTP_SHARE_10K = 0.008
MODE_MAX_P = {
    "base": 1 / 1_000_000,
    "base_ante": 1 / 700_000,
    "feature_spin": 1 / 80_000,
    "peak_spin": 1 / 4_000,
    "bonus_see": 1 / 40_000,
    "bonus_hear": 1 / 20_000,
    "bonus_gamble": 1 / 4_500,
}
MODE_ZERO_BAND = {
    "base": (0.45, 0.60),
    "base_ante": (0.45, 0.60),
    "feature_spin": (0.50, 0.62),
    "peak_spin": (0.55, 0.75),
    "bonus_see": (0.0, 0.04),
    "bonus_hear": (0.0, 0.04),
    "bonus_gamble": (0.47, 0.53),
}
MODE_PROFIT_MIN = {
    "base": 0.15,
    "base_ante": 0.12,
    "feature_spin": 0.20,
    "peak_spin": 0.20,
    "bonus_see": 0.30,
    "bonus_hear": 0.30,
    "bonus_gamble": 0.15,
}
MID_PAYOUT_LO = 1_500
MID_PAYOUT_HI = 4_500


def read_lut(path: Path) -> list[tuple[int, int, int]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            sim_id, weight, payout = line.strip().split(",")
            rows.append((int(sim_id), int(weight), int(payout)))
    return rows


def rtp_from_rows(rows: list[tuple[int, int, int]], cost: float) -> float:
    total_w = sum(weight for _, weight, _ in rows)
    avg_x = sum(weight * payout for _, weight, payout in rows) / total_w / 100.0
    return avg_x / cost


def tail_rtp_share(rows: list[tuple[int, int, int]], cost: float, threshold: int) -> float:
    total_w = sum(weight for _, weight, _ in rows)
    total_ev = sum(weight * payout for _, weight, payout in rows) / total_w / 100.0 / cost
    tail_ev = sum(weight * payout for _, weight, payout in rows if payout >= threshold) / total_w / 100.0 / cost
    return tail_ev / total_ev if total_ev > 0 else 0.0


def weighted_std(rows: list[tuple[int, int, int]], cost: float) -> float:
    total_w = sum(weight for _, weight, _ in rows)
    mean = sum(weight * payout for _, weight, payout in rows) / total_w / 100.0 / cost
    var = sum(weight * ((payout / 100.0 / cost - mean) ** 2) for _, weight, payout in rows) / total_w
    return var**0.5


def vol_skew_factor(payout: int, skew: float) -> float:
    if payout <= 0:
        return max(0.2, 1.0 - 0.55 * skew)
    if payout < MID_PAYOUT_LO:
        return max(0.3, 1.0 - 0.25 * skew)
    if payout <= MID_PAYOUT_HI:
        return 1.0 + 5.0 * skew
    return max(0.4, 1.0 - 0.35 * skew)


def uniform_weights(rows: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    equal = max(1, TOTAL_WEIGHT // len(rows))
    remainder = TOTAL_WEIGHT - equal * len(rows)
    weighted = []
    for i, (sim_id, _, payout) in enumerate(rows):
        weight = equal + (1 if i < remainder else 0)
        weighted.append((sim_id, weight, payout))
    return weighted


def _allocate(raw: list[float], budget: int, floor: int = 1) -> list[int]:
    """Largest-remainder split of budget. Each entry stays at least `floor` when it fits."""
    if not raw:
        return []
    budget = max(budget, floor * len(raw))
    total = sum(raw) or 1.0
    exact = [weight / total * budget for weight in raw]
    weights = [max(floor, int(math.floor(weight))) for weight in exact]
    short = budget - sum(weights)
    order = sorted(range(len(exact)), key=lambda i: exact[i] - math.floor(exact[i]), reverse=True)
    cursor = 0
    while short > 0 and order:
        weights[order[cursor % len(order)]] += 1
        short -= 1
        cursor += 1
    while short < 0:
        donor = max(range(len(weights)), key=lambda i: weights[i])
        if weights[donor] <= floor:
            break
        weights[donor] -= 1
        short += 1
    return weights


def _nudge_to_target(
    weighted: list[tuple[int, int, int]],
    target_sum: float,
) -> list[tuple[int, int, int]]:
    """Move weight between two rows until the weighted payout sum matches the target."""
    total_w = sum(weight for _, weight, _ in weighted)
    current_sum = sum(weight * payout for _, weight, payout in weighted)
    delta = target_sum * (total_w / TOTAL_WEIGHT) - current_sum
    if abs(delta) < 1:
        return weighted
    zeros = [i for i, (_, weight, payout) in enumerate(weighted) if payout <= 0 and weight > 1]
    hits = [i for i, (_, weight, payout) in enumerate(weighted) if payout > 0 and weight > 1]
    if not hits:
        return weighted
    if zeros:
        source = zeros[0]
        dest = min(hits, key=lambda i: weighted[i][2])
        payout = weighted[dest][2]
        move = int(round(delta / payout))
        move = max(-(weighted[dest][1] - 1), min(move, weighted[source][1] - 1))
    else:
        ordered = sorted(hits, key=lambda i: weighted[i][2])
        source = ordered[0]
        dest = ordered[-1]
        gap = weighted[dest][2] - weighted[source][2]
        if gap <= 0:
            return weighted
        move = int(round(delta / gap))
        move = max(-(weighted[dest][1] - 1), min(move, weighted[source][1] - 1))
    if move == 0:
        return weighted
    s_id, s_w, s_p = weighted[source]
    d_id, d_w, d_p = weighted[dest]
    weighted[source] = (s_id, s_w - move, s_p)
    weighted[dest] = (d_id, d_w + move, d_p)
    return weighted


def assign_weights(
    rows: list[tuple[int, int, int]],
    cost: float,
    target_rtp: float = TARGET_RTP,
    target_std: float | None = None,
    max_gamma: float = 12.0,
) -> list[tuple[int, int, int]]:
    del target_std
    target_avg_hundredths = target_rtp * cost * 100.0
    payouts = [payout for _, _, payout in rows]
    uniform_rtp = (sum(payouts) / len(payouts) / 100.0 / cost) if payouts else 0.0
    zero_count = sum(1 for payout in payouts if payout <= 0)
    # Already near the target: only move weight between misses and hits.
    # Crushing the tail here would delete the 50/40/10 gamble mix.
    if zero_count and abs(uniform_rtp - target_rtp) / target_rtp <= 0.05:
        hit_idx = [i for i, payout in enumerate(payouts) if payout > 0]
        zero_idx = [i for i, payout in enumerate(payouts) if payout <= 0]
        hit_mean = sum(payouts[i] for i in hit_idx) / len(hit_idx)
        target_sum = target_avg_hundredths * TOTAL_WEIGHT
        need = target_sum / hit_mean
        pos_budget = int(round(min(max(need, len(hit_idx)), TOTAL_WEIGHT - len(zero_idx))))
        per_hit, extra = divmod(pos_budget, len(hit_idx))
        per_hit = max(1, per_hit)
        zero_budget = TOTAL_WEIGHT - (per_hit * len(hit_idx) + extra)
        per_zero, zero_extra = divmod(max(zero_budget, len(zero_idx)), len(zero_idx))
        weighted: list[tuple[int, int, int]] = []
        h_seen = 0
        z_seen = 0
        for idx, (sim_id, _, payout) in enumerate(rows):
            if payout <= 0:
                weight = per_zero + (1 if z_seen < zero_extra else 0)
                z_seen += 1
            else:
                weight = per_hit + (1 if h_seen < extra else 0)
                h_seen += 1
            weighted.append((sim_id, max(1, weight), payout))
        return _nudge_to_target(weighted, target_sum)

    max_indices = {i for i, p in enumerate(payouts) if p >= MAX_WIN_PAYOUT}
    high_5k_indices = {i for i, p in enumerate(payouts) if PAYOUT_5K <= p < MAX_WIN_PAYOUT}

    max_tail_rtp = MAX_TAIL_RTP_SHARE_10K * target_rtp
    max_total_weight = max(
        len(max_indices),
        int(max_tail_rtp * TOTAL_WEIGHT * 100 / MAX_WIN_PAYOUT),
    )
    per_max_weight = max(1, max_total_weight // max(len(max_indices), 1))

    if high_5k_indices:
        avg_5k_payout = sum(payouts[i] for i in high_5k_indices) / len(high_5k_indices)
        tail_5k_rtp = max(
            0.0,
            MAX_TAIL_RTP_SHARE_5K * target_rtp
            - (per_max_weight * len(max_indices) * MAX_WIN_PAYOUT) / (TOTAL_WEIGHT * 100),
        )
        high_5k_total_weight = max(
            len(high_5k_indices),
            int(tail_5k_rtp * TOTAL_WEIGHT * 100 / max(avg_5k_payout, 1)),
        )
        per_5k_weight = max(1, high_5k_total_weight // len(high_5k_indices))
    else:
        per_5k_weight = 0

    reserved = per_max_weight * len(max_indices) + per_5k_weight * len(high_5k_indices)
    remaining_budget = TOTAL_WEIGHT - reserved
    if remaining_budget <= 0:
        raise RuntimeError("Tail rows consume entire weight budget")

    heavy_tail = max_indices | high_5k_indices
    non_max_indices = [i for i in range(len(rows)) if i not in heavy_tail]
    zero_indices = {i for i in non_max_indices if payouts[i] <= 0}
    positive_indices = [i for i in non_max_indices if i not in zero_indices]

    max_contrib = per_max_weight * MAX_WIN_PAYOUT * len(max_indices)
    high_contrib = per_5k_weight * sum(payouts[i] for i in high_5k_indices)
    tail_sum = max_contrib + high_contrib
    target_sum = target_avg_hundredths * TOTAL_WEIGHT

    def positive_mean(gamma: float) -> float:
        if not positive_indices:
            return 0.0
        logs = [-gamma * math.log(payouts[i]) for i in positive_indices]
        peak = max(logs)
        shaped = [math.exp(value - peak) for value in logs]
        total = sum(shaped)
        return sum(weight * payouts[i] for weight, i in zip(shaped, positive_indices)) / total

    def gamma_for_mean(desired: float) -> float:
        """Tilt positive rows until their weighted mean matches desired hundredths."""
        if not positive_indices:
            return 0.0
        lo, hi = -6.0, max(max_gamma, 40.0)
        for _ in range(60):
            mid = (lo + hi) / 2.0
            if positive_mean(mid) > desired:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    if positive_indices:
        if zero_indices:
            # Keep the simulated win shape. Move weight between misses and hits
            # until the average matches the target. Tilt only if equal weights
            # on the winning rows cannot reach it.
            equal_mean = positive_mean(0.0)
            need = (target_sum - tail_sum) / equal_mean if equal_mean else remaining_budget
            if 0 < need <= remaining_budget:
                gamma = 0.0
                pos_budget = int(round(need))
            elif need > remaining_budget:
                desired = (target_sum - tail_sum) / remaining_budget
                gamma = gamma_for_mean(desired)
                pos_budget = remaining_budget
            else:
                gamma = gamma_for_mean(max(min(payouts[i] for i in positive_indices), 1))
                pos_budget = max(len(positive_indices), int(round(max(need, 0))))
        else:
            desired = (target_sum - tail_sum) / remaining_budget
            gamma = gamma_for_mean(max(desired, 1.0))
            pos_budget = remaining_budget
        pos_budget = min(max(pos_budget, len(positive_indices)), remaining_budget - (len(zero_indices) if zero_indices else 0))
        pos_budget = max(pos_budget, len(positive_indices))
        logs = [-gamma * math.log(payouts[i]) for i in positive_indices]
        peak = max(logs)
        shaped = [math.exp(value - peak) for value in logs]
        total_shaped = sum(shaped) or 1.0
        raw_pos = [weight / total_shaped * pos_budget for weight in shaped]
        pos_weights = [max(1, int(math.floor(weight))) for weight in raw_pos]
        short = pos_budget - sum(pos_weights)
        order = sorted(range(len(raw_pos)), key=lambda i: raw_pos[i] - math.floor(raw_pos[i]), reverse=True)
        cursor = 0
        while short > 0 and order:
            pos_weights[order[cursor % len(order)]] += 1
            short -= 1
            cursor += 1
        while short < 0:
            donor = max(range(len(pos_weights)), key=lambda i: pos_weights[i])
            if pos_weights[donor] <= 1:
                break
            pos_weights[donor] -= 1
            short += 1
        pos_weight_by_index = {index: weight for index, weight in zip(positive_indices, pos_weights)}
    else:
        pos_weight_by_index = {}
        pos_budget = 0

    zero_budget = remaining_budget - sum(pos_weight_by_index.values())
    if zero_indices:
        per_zero = max(1, zero_budget // len(zero_indices))
        zero_extra = zero_budget - per_zero * len(zero_indices)
    else:
        per_zero = 0
        zero_extra = 0

    weighted: list[tuple[int, int, int]] = []
    zero_seen = 0
    for idx, (sim_id, _, payout) in enumerate(rows):
        if idx in max_indices:
            weight = per_max_weight
        elif idx in high_5k_indices:
            weight = per_5k_weight
        elif idx in zero_indices:
            weight = per_zero + (1 if zero_seen < zero_extra else 0)
            zero_seen += 1
        else:
            weight = pos_weight_by_index.get(idx, 1)
        weighted.append((sim_id, max(1, weight), payout))

    return _nudge_to_target(weighted, target_sum)


def write_lut(path: Path, rows: list[tuple[int, int, int]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for sim_id, weight, payout in rows:
            handle.write(f"{sim_id},{weight},{payout}\n")


def restore_from_lookup(mode: str) -> None:
    src = LOOKUP / f"lookUpTable_{mode}.csv"
    dst = PUBLISH / f"lookUpTable_{mode}_0.csv"
    if src.exists():
        write_lut(dst, read_lut(src))


def shape_reweight(
    rows: list[tuple[int, int, int]],
    cost: float,
    target_rtp: float,
    max_p: float,
    zero_band: tuple[float, float],
    profit_min: float,
) -> list[tuple[int, int, int]]:
    """Hit the RTP target while keeping the simulated zero rate and a profit floor.

    Max-win rows are pinned to ``max_p``. Weight moves among paying rows. It is not
    dumped onto misses.
    """
    payouts = [payout for _, _, payout in rows]
    count = len(rows)
    profit_line = cost * 100.0
    zero_idx = [i for i, payout in enumerate(payouts) if payout <= 0]
    max_idx = [i for i, payout in enumerate(payouts) if payout >= MAX_WIN_PAYOUT]
    profit_idx = [i for i, payout in enumerate(payouts) if profit_line < payout < MAX_WIN_PAYOUT]
    small_idx = [i for i, payout in enumerate(payouts) if 0 < payout <= profit_line]
    natural_zero = len(zero_idx) / count
    natural_profit = len(profit_idx) / count
    lo, hi = zero_band
    zero_rate = natural_zero if lo <= natural_zero <= hi else min(max(natural_zero, lo), hi)
    if not zero_idx:
        zero_rate = 0.0
    if not max_idx:
        max_p = 0.0
    profit_rate = max(natural_profit, profit_min if profit_idx else 0.0)
    if not profit_idx:
        profit_rate = 0.0
    profit_rate = min(profit_rate, max(0.0, 1.0 - zero_rate - max_p))
    small_rate = max(0.0, 1.0 - zero_rate - max_p - profit_rate)
    if not small_idx:
        profit_rate += small_rate
        small_rate = 0.0

    def masses(gamma: float) -> dict[int, float]:
        raw: dict[int, float] = {}

        def fill(indexes: list[int], rate: float, tilt: bool) -> None:
            if not indexes or rate <= 0:
                return
            if tilt:
                logs = [math.exp(-gamma * math.log(max(payouts[i], 1))) for i in indexes]
                scale = sum(logs) or 1.0
                for index, shaped in zip(indexes, logs):
                    raw[index] = rate * shaped / scale
            else:
                share = rate / len(indexes)
                for index in indexes:
                    raw[index] = share

        fill(max_idx, max_p, False)
        fill(zero_idx, zero_rate, False)
        fill(profit_idx, profit_rate, True)
        fill(small_idx, small_rate, True)
        return raw

    def rtp_of(gamma: float) -> float:
        raw = masses(gamma)
        return sum(raw[i] * payouts[i] for i in raw) / 100.0 / cost

    low_gamma, high_gamma = -4.0, 12.0
    if rtp_of(0.0) > target_rtp:
        for _ in range(40):
            mid = (low_gamma + high_gamma) / 2.0
            if rtp_of(mid) > target_rtp:
                low_gamma = mid
            else:
                high_gamma = mid
        gamma = high_gamma
    else:
        for _ in range(40):
            mid = (low_gamma + high_gamma) / 2.0
            if rtp_of(mid) < target_rtp:
                high_gamma = mid
            else:
                low_gamma = mid
        gamma = low_gamma
    raw = masses(gamma)
    weighted = [(rows[i][0], max(1, int(round(raw.get(i, 0.0) * TOTAL_WEIGHT))), payouts[i]) for i in range(count)]
    target_sum = target_rtp * cost * 100.0 * TOTAL_WEIGHT
    return _nudge_to_target(weighted, target_sum)


def reweight_mode(mode: str, restore: bool = False) -> dict:
    cost = MODE_COSTS[mode]
    if restore:
        restore_from_lookup(mode)
    lut_path = PUBLISH / f"lookUpTable_{mode}_0.csv"
    if not lut_path.exists():
        raise RuntimeError(f"Missing LUT: {lut_path}")
    rows = read_lut(lut_path)
    before = rtp_from_rows(rows, cost)
    target = MODE_TARGET_RTP.get(mode, TARGET_RTP)
    weighted = shape_reweight(
        rows,
        cost,
        target,
        MODE_MAX_P.get(mode, 0.0),
        MODE_ZERO_BAND.get(mode, (0.0, 1.0)),
        MODE_PROFIT_MIN.get(mode, 0.0),
    )
    write_lut(lut_path, weighted)
    after = rtp_from_rows(weighted, cost)
    return {"mode": mode, "cost": cost, "rows": len(rows), "rtp_before": before, "rtp_after": after}


def reweight_all(restore: bool = False, modes: list[str] | None = None) -> list[dict]:
    summary = []
    target_modes = modes or list(MODE_COSTS.keys())
    for mode in target_modes:
        summary.append(reweight_mode(mode, restore=restore))
    out = GAME_DIR / "library" / "reweight_summary.json"
    existing = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    by_mode = {item["mode"]: item for item in existing}
    for item in summary:
        by_mode[item["mode"]] = item
    out.write_text(json.dumps(list(by_mode.values()), indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import sys

    restore = "--restore" in sys.argv
    for item in reweight_all(restore=restore):
        print(
            f"{item['mode']}: rows={item['rows']} "
            f"rtp {item['rtp_before']:.4f} -> {item['rtp_after']:.4f}"
        )
