"""Retarget publish LUT weights to 96.01% RTP while preserving book/LUT payout parity."""

from __future__ import annotations

import json
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent
PUBLISH = GAME_DIR / "library" / "publish_files"
LOOKUP = GAME_DIR / "library" / "lookup_tables"

MODE_COSTS = {
    "base": 1.0,
    "base_ante": 1.4,
    "feature_spin": 50.0,
    "peak_spin": 1000.0,
    "bonus_see": 100.0,
    "bonus_hear": 200.0,
    "bonus_gamble": 1567.0,
}

TARGET_RTP = 0.9601
MODE_TARGET_RTP = {mode: TARGET_RTP for mode in MODE_COSTS}
# LUT payouts are in bet-hundredths. 25,000× = 2,500,000.
MAX_WIN_PAYOUT = 2_500_000
PAYOUT_5K = 500_000
TOTAL_WEIGHT = 10_000_000_000
MAX_TAIL_RTP_SHARE_5K = 0.010
MAX_TAIL_RTP_SHARE_10K = 0.008
TARGET_WEIGHTED_STD = {}
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


def assign_weights(
    rows: list[tuple[int, int, int]],
    cost: float,
    target_rtp: float = TARGET_RTP,
    target_std: float | None = None,
    max_gamma: float = 12.0,
) -> list[tuple[int, int, int]]:
    target_avg_hundredths = target_rtp * cost * 100.0
    payouts = [payout for _, _, payout in rows]

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

    non_max_payouts = [max(payouts[i], 1) for i in non_max_indices]

    lo, hi = 0.0, max_gamma
    for _ in range(80):
        gamma = (lo + hi) / 2.0
        raw = [(target_avg_hundredths / payout) ** gamma for payout in non_max_payouts]
        total_raw = sum(raw)
        avg_non_max = sum(r * p for r, p in zip(raw, non_max_payouts)) / total_raw
        max_contrib = per_max_weight * MAX_WIN_PAYOUT * len(max_indices)
        high_contrib = per_5k_weight * sum(payouts[i] for i in high_5k_indices)
        blended = (remaining_budget * avg_non_max + max_contrib + high_contrib) / TOTAL_WEIGHT
        if blended > target_avg_hundredths:
            lo = gamma
        else:
            hi = gamma

    gamma = (lo + hi) / 2.0
    raw = [(target_avg_hundredths / payout) ** gamma for payout in non_max_payouts]
    total_raw = sum(raw)
    non_max_weights = [int(round(w / total_raw * remaining_budget)) for w in raw]
    for i, w in enumerate(non_max_weights):
        if w < 1:
            non_max_weights[i] = 1

    if target_std is not None and zero_indices and positive_indices:
        pos_payout_values = [payouts[i] for i in positive_indices]
        spike_payout = 1_500
        best_weights = list(non_max_weights)
        best_std = 0.0
        for zero_share in (0.10, 0.12, 0.14, 0.16, 0.18):
            for mid_boost in (2.0, 3.0, 4.0, 5.0, 6.0):
                for spike_share in (0.01, 0.015, 0.02, 0.025):
                    zero_budget = max(len(zero_indices), int(remaining_budget * zero_share))
                    spike_budget = max(1, int(remaining_budget * spike_share))
                    positive_budget = remaining_budget - zero_budget - spike_budget
                    if positive_budget <= len(positive_indices):
                        continue
                    per_zero = max(1, zero_budget // len(zero_indices))
                    spike_indices = [i for i in positive_indices if payouts[i] == spike_payout]
                    other_indices = [i for i in positive_indices if payouts[i] != spike_payout]
                    per_spike = max(1, spike_budget // max(len(spike_indices), 1)) if spike_indices else 0
                    raw = []
                    for i in other_indices:
                        p = max(payouts[i], 1)
                        boost = mid_boost if MID_PAYOUT_LO <= p <= MID_PAYOUT_HI else 1.0
                        raw.append((p**0.35) * boost)
                    total_raw = sum(raw) or 1.0
                    other_weights = {
                        i: max(1, int(round(w / total_raw * positive_budget)))
                        for i, w in zip(other_indices, raw)
                    }
                    trial_rows: list[tuple[int, int, int]] = []
                    for idx, (sim_id, _, payout) in enumerate(rows):
                        if idx in max_indices:
                            trial_rows.append((sim_id, per_max_weight, payout))
                        elif idx in high_5k_indices:
                            trial_rows.append((sim_id, per_5k_weight, payout))
                        elif idx in zero_indices:
                            trial_rows.append((sim_id, per_zero, payout))
                        elif payout == spike_payout and spike_indices:
                            trial_rows.append((sim_id, per_spike, payout))
                        else:
                            trial_rows.append((sim_id, other_weights[idx], payout))
                    std = weighted_std(trial_rows, cost)
                    rtp = rtp_from_rows(trial_rows, cost)
                    if abs(rtp - target_rtp) <= 0.008 and std > best_std:
                        best_std = std
                        rebuilt: list[int] = []
                        for idx in non_max_indices:
                            if idx in zero_indices:
                                rebuilt.append(per_zero)
                            elif payouts[idx] == spike_payout and spike_indices:
                                rebuilt.append(per_spike)
                            else:
                                rebuilt.append(other_weights[idx])
                        best_weights = rebuilt
        non_max_weights = best_weights

    weighted: list[tuple[int, int, int]] = []
    non_ptr = 0
    for idx, (sim_id, _, payout) in enumerate(rows):
        if idx in max_indices:
            weighted.append((sim_id, per_max_weight, payout))
        elif idx in high_5k_indices:
            weighted.append((sim_id, per_5k_weight, payout))
        else:
            weighted.append((sim_id, non_max_weights[non_ptr], payout))
            non_ptr += 1
    return weighted


def write_lut(path: Path, rows: list[tuple[int, int, int]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for sim_id, weight, payout in rows:
            handle.write(f"{sim_id},{weight},{payout}\n")


def restore_from_lookup(mode: str) -> None:
    src = LOOKUP / f"lookUpTable_{mode}.csv"
    dst = PUBLISH / f"lookUpTable_{mode}_0.csv"
    if src.exists():
        write_lut(dst, read_lut(src))


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
    if abs(before - target) <= max(0.02, target * 0.025) and before >= target * 0.97:
        weighted = uniform_weights(rows)
        write_lut(lut_path, weighted)
        after = rtp_from_rows(weighted, cost)
        return {"mode": mode, "cost": cost, "rows": len(rows), "rtp_before": before, "rtp_after": after}
    target_std = TARGET_WEIGHTED_STD.get(mode)
    max_gamma = 40.0 if before > target * 2 else 12.0
    weighted = assign_weights(rows, cost, target_rtp=target, target_std=target_std, max_gamma=max_gamma)
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
