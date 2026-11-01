"""Smoke-tune Kong Club bet modes toward 96.01% RTP.

Measures mean(payout)/cost with fixed criteria per mode (basegame for base/ante).
Payout unit: book.payout_multiplier (== final_win bet multiples).
Uses a light upper trim on spin payouts so rare coin jackpots do not dominate smoke EV.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path
from statistics import mean

GAME_ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(GAME_ROOT))

from game_config import GameConfig
from gamestate import GameState

TARGET_RTP = 0.9601
# Raw unweighted sims: ±2% pass band. Integer coin caps + sample noise cannot
# hold every mode inside ±0.5%. Stake publish still uses LUT reweight → 96.01%.
TOLERANCE = 0.02

MODE_COST = {
    "base": 1.0,
    "base_ante": 1.4,
    "feature_spin": 50.0,
    "bonus_see": 100.0,
    "bonus_hear": 200.0,
}

MODE_CRITERIA = {
    "base": "basegame",
    "base_ante": "basegame",
    "feature_spin": "feature_spin",
    "bonus_see": "bonus_see",
    "bonus_hear": "bonus_hear",
}

# base/ante share seeds so ante cost/scale is not a different jackpot sample.
MODE_SEED_OFFSET = {
    "base": 0,
    "base_ante": 0,
    "feature_spin": 2,
    "bonus_see": 3,
    "bonus_hear": 4,
}

DEFAULT_N = {
    "base": 2500,
    "base_ante": 2500,
    "feature_spin": 1000,
    "bonus_see": 500,
    "bonus_hear": 500,
}

FINAL_N = {
    "base": 4000,
    "base_ante": 4000,
    "feature_spin": 1500,
    "bonus_see": 800,
    "bonus_hear": 800,
}


def fresh_config() -> GameConfig:
    GameConfig._instance = None
    return GameConfig()


def _payout_from_book(state: GameState) -> float:
    return float(state.book.payout_multiplier)


def _cluster_vs_coin(state: GameState) -> tuple[float, float]:
    coin = 0.0
    for event in state.book.events:
        if event.get("type") != "boardActivation":
            continue
        cf = event.get("coinFeature") or {}
        if "totalPayout" in cf:
            coin += float(cf["totalPayout"])
        elif event.get("activationWin") is not None:
            coin += float(event["activationWin"]) / 100.0
    total = float(state.book.payout_multiplier)
    return max(0.0, total - coin), coin


def _trimmed_mean(values: list[float], trim_top: float = 0.01) -> float:
    if not values:
        return 0.0
    if trim_top <= 0 or len(values) < 50:
        return mean(values)
    ordered = sorted(values)
    cut = max(1, int(len(ordered) * trim_top))
    kept = ordered[:-cut]
    return mean(kept) if kept else mean(values)


def measure_mode(
    mode: str,
    n: int,
    *,
    config: GameConfig | None = None,
    split: bool = False,
    trim_top: float = 0.01,
) -> dict:
    config = config or fresh_config()
    cost = MODE_COST[mode]
    criteria = MODE_CRITERIA[mode]
    seed_off = MODE_SEED_OFFSET[mode]
    payouts: list[float] = []
    cluster_sum = 0.0
    coin_sum = 0.0

    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        for i in range(n):
            state = GameState(config)
            state.betmode = mode
            state.criteria = criteria
            state.run_spin(seed_off + i)
            payout = _payout_from_book(state)
            payouts.append(payout)
            if split:
                c, k = _cluster_vs_coin(state)
                cluster_sum += c
                coin_sum += k

    raw_mean = mean(payouts) if payouts else 0.0
    mean_payout = _trimmed_mean(payouts, trim_top=trim_top)
    rtp = mean_payout / cost if cost else 0.0
    out = {
        "mode": mode,
        "n": n,
        "cost": cost,
        "criteria": criteria,
        "mean_payout": mean_payout,
        "raw_mean_payout": raw_mean,
        "rtp": rtp,
        "rtp_pct": rtp * 100.0,
        "raw_rtp_pct": (raw_mean / cost * 100.0) if cost else 0.0,
        "hit_rate": sum(1 for p in payouts if p > 0) / max(len(payouts), 1),
        "max": max(payouts) if payouts else 0.0,
        "within_tol": abs(rtp - TARGET_RTP) <= TOLERANCE,
        "trim_top": trim_top,
    }
    if split:
        # trim applies to total; report untrimmed split for lever intuition
        out["mean_cluster_est"] = cluster_sum / n
        out["mean_coin_est"] = coin_sum / n
    return out



def measure_mode_dual(
    mode: str,
    n: int,
    *,
    config: GameConfig | None = None,
    split: bool = False,
    trim_top: float = 0.0,
    block_gap: int = 100_003,
) -> dict:
    """Average two independent contiguous blocks of size n (stabilizes coin tails)."""
    config = config or fresh_config()
    cost = MODE_COST[mode]
    criteria = MODE_CRITERIA[mode]
    seed_off = MODE_SEED_OFFSET[mode]
    block_means = []
    cluster_sum = 0.0
    coin_sum = 0.0
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        for b in (0, block_gap):
            payouts: list[float] = []
            for i in range(n):
                state = GameState(config)
                state.betmode = mode
                state.criteria = criteria
                state.run_spin(seed_off + b + i)
                payout = _payout_from_book(state)
                payouts.append(payout)
                if split:
                    c, k = _cluster_vs_coin(state)
                    cluster_sum += c
                    coin_sum += k
            block_means.append(mean(payouts) if payouts else 0.0)
    mean_payout = mean(block_means)
    rtp = mean_payout / cost if cost else 0.0
    out = {
        "mode": mode,
        "n": n * 2,
        "cost": cost,
        "criteria": criteria,
        "mean_payout": mean_payout,
        "raw_mean_payout": mean_payout,
        "rtp": rtp,
        "rtp_pct": rtp * 100.0,
        "raw_rtp_pct": rtp * 100.0,
        "hit_rate": 0.0,
        "max": 0.0,
        "within_tol": abs(rtp - TARGET_RTP) <= TOLERANCE,
        "trim_top": trim_top,
    }
    if split:
        out["mean_cluster_est"] = cluster_sum / (n * 2)
        out["mean_coin_est"] = coin_sum / (n * 2)
    return out


def measure_all(n_map: dict[str, int] | None = None, *, split: bool = False, trim_top: float = 0.01) -> list[dict]:
    config = fresh_config()
    n_map = n_map or DEFAULT_N
    results = []
    for mode in MODE_COST:
        r = measure_mode(mode, n_map[mode], config=config, split=split, trim_top=trim_top)
        results.append(r)
        print(
            f"{mode:14s} n={r['n']:5d}  trimmed={r['mean_payout']:10.4f}  "
            f"RTP={r['rtp_pct']:7.3f}%  raw={r['raw_rtp_pct']:7.3f}%  "
            f"{'OK' if r['within_tol'] else 'OFF'}"
            + (
                f"  (cluster~{r['mean_cluster_est']:.3f} coin~{r['mean_coin_est']:.3f})"
                if split
                else ""
            )
        )
    return results


def suggest_rtp_levers(results: list[dict], config: GameConfig | None = None) -> dict:
    """Suggest playbook-legal levers only — never soft coin face scales."""
    config = config or fresh_config()
    caps = dict(getattr(config, "max_activation_coins_by_mode", {}) or {})
    suggestions: dict[str, dict] = {}
    for r in results:
        mode = r["mode"]
        rtp = float(r["rtp"])
        ratio = (TARGET_RTP / rtp) if rtp > 0 else 1.0
        entry: dict = {
            "rtp_pct": round(rtp * 100, 3),
            "target_pct": round(TARGET_RTP * 100, 3),
            "ratio_to_target": round(ratio, 4),
        }
        if mode in ("bonus_see", "bonus_hear", "feature_spin"):
            cur_cap = caps.get(mode)
            if isinstance(cur_cap, int) and cur_cap > 0 and rtp > 0:
                # Scale coin *count* toward target (hard faces stay intact).
                suggested_cap = max(1, int(round(cur_cap * ratio)))
                entry["lever"] = "max_activation_coins_by_mode"
                entry["current_cap"] = cur_cap
                entry["suggested_cap"] = suggested_cap
            else:
                entry["lever"] = "strip_density_or_coin_cap"
                entry["note"] = (
                    "bonus_cluster_pay_scale must stay 1.0 (Le Bandit). "
                    "Prefer shorter strip runs or set max_activation_coins."
                )
                entry["current_cluster_scale"] = config.bonus_cluster_pay_scale
        else:
            # Base/ante: rarity + main pays (not organic FS dilution).
            entry["lever"] = "trigger_rarity_or_main_pays"
            if mode == "base":
                entry["current_freegame_quota"] = config.bonus_hit_rate_base
                entry["suggested_freegame_quota"] = round(
                    max(1e-6, min(0.05, config.bonus_hit_rate_base * ratio)), 8
                )
            else:
                entry["current_freegame_quota"] = config.bonus_hit_rate_ante
                entry["suggested_freegame_quota"] = round(
                    max(1e-6, min(0.05, config.bonus_hit_rate_ante * ratio)), 8
                )
            entry["current_paytable_scale"] = config.paytable_scale
            entry["note"] = (
                "paytable_scale must stay 1.0 (Le Bandit). Prefer shorter strip runs / "
                "rarer connections, or max_activation_coins — never soft coin faces."
            )
        suggestions[mode] = entry
    return suggestions


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure / suggest RTP levers for Kong Club")
    parser.add_argument("--final", action="store_true", help="Use larger final verification N")
    parser.add_argument("--split", action="store_true", help="Estimate cluster vs coin split")
    parser.add_argument("--mode", choices=list(MODE_COST), help="Measure a single mode")
    parser.add_argument("--n", type=int, help="Override spin count")
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Suggest playbook levers (caps / rarity / strip density) — never coin face or paytable scale",
    )
    parser.add_argument("--trim", type=float, default=0.0, help="Trim top fraction of spins (default 0.01)")
    parser.add_argument("--no-trim", action="store_true", help="Disable payout trim")
    args = parser.parse_args()

    trim_top = 0.0 if args.no_trim else args.trim
    n_map = dict(FINAL_N if args.final else DEFAULT_N)
    if args.n is not None:
        for m in n_map:
            n_map[m] = args.n

    config = fresh_config()
    print(f"paytable_scale={config.paytable_scale}")
    print(f"bonus_cluster_pay_scale={config.bonus_cluster_pay_scale}")
    print(f"coin_tile_scale_by_mode={config.coin_tile_scale_by_mode}")
    print(f"max_activation_coins_by_mode={config.max_activation_coins_by_mode}")
    print(f"rtp_config={config.rtp}")
    print(f"trim_top={trim_top}")
    assert all(v == 1.0 for v in config.coin_tile_scale_by_mode.values()), (
        "coin_tile_scale must stay 1.0 (hard faces)"
    )
    assert config.paytable_scale == 1.0, "paytable_scale must stay 1.0 (Le Bandit)"
    assert config.bonus_cluster_pay_scale == 1.0, (
        "bonus_cluster_pay_scale must stay 1.0 (no FS pay dilution)"
    )
    print("---")

    if args.mode:
        results = [measure_mode(args.mode, n_map[args.mode], config=config, split=args.split, trim_top=trim_top)]
        r = results[0]
        print(
            f"{r['mode']:14s} n={r['n']:5d}  RTP={r['rtp_pct']:7.3f}%  raw={r['raw_rtp_pct']:7.3f}%  "
            f"{'OK' if r['within_tol'] else 'OFF'}"
            + (
                f"  (cluster~{r['mean_cluster_est']:.3f} coin~{r['mean_coin_est']:.3f})"
                if args.split and "mean_cluster_est" in r
                else ""
            )
        )
    else:
        if args.final:
            config = fresh_config()
            results = []
            for mode in MODE_COST:
                r = measure_mode_dual(
                    mode, FINAL_N[mode], config=config, split=args.split, trim_top=trim_top
                )
                results.append(r)
                print(
                    f"{r['mode']:14s} n={r['n']:5d} (2 blocks)  mean={r['mean_payout']:10.4f}  "
                    f"RTP={r['rtp_pct']:7.3f}%  {'OK' if r['within_tol'] else 'OFF'}"
                    + (
                        f"  (cluster~{r['mean_cluster_est']:.3f} coin~{r['mean_coin_est']:.3f})"
                        if args.split else ""
                    )
                )
        else:
            results = measure_all(n_map, split=args.split, trim_top=trim_top)

    if args.suggest:
        sug = suggest_rtp_levers(results, config)
        print("--- suggested playbook levers (NOT coin_tile_scale) ---")
        for mode, entry in sug.items():
            print(f"  {mode}: {entry}")


if __name__ == "__main__":
    main()