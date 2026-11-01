"""Long cost-aware RTP audit for Monkey Mayhem (playbook).

Reports per mode: RTP, hit rate, % profitable (buys), max paid.
Base/ante mix freegame criteria at certified quotas and use **weighted** RTP
(same idea as warm_fe_math_cache / Stake LUT weighting).

Usage:
  python scripts/math_rtp_audit.py --quick
  python scripts/math_rtp_audit.py --buys 10000 --base 25000
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import random
import sys
from pathlib import Path

GAME_ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(GAME_ROOT))

from game_config import GameConfig
from gamestate import GameState

TARGET_RTP = 0.9601
# Align with tune_rtp_9601: ±2% raw-sim band (LUT reweight for exact Stake 96.01%).
RTP_TOLERANCE = 0.02

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

MODE_SEED_OFFSET = {
    "base": 0,
    "base_ante": 0,
    "feature_spin": 2,
    "bonus_see": 3,
    "bonus_hear": 4,
}


def fresh_config() -> GameConfig:
    GameConfig._instance = None
    return GameConfig()


def _freegame_quota(config: GameConfig, mode: str) -> float:
    if mode == "base_ante":
        return float(config.bonus_hit_rate_ante)
    if mode == "base":
        return float(config.bonus_hit_rate_base)
    return 0.0


def _is_freegame_book(gs: GameState) -> bool:
    return any(
        e.get("type") == "freeSpinTrigger"
        or (
            e.get("type") == "monkeyMayhemMode"
            and str(e.get("state", "")).startswith("organic_bonus_")
        )
        for e in gs.book.events
    )


def audit_mode(mode: str, n: int, *, config: GameConfig | None = None) -> dict:
    config = config or fresh_config()
    cost = MODE_COST[mode]
    seed_off = MODE_SEED_OFFSET[mode]
    quota = _freegame_quota(config, mode)
    sink = io.StringIO()

    if mode in ("base", "base_ante") and quota > 0:
        n_fg = max(20, int(round(n * quota * 12)))
        n_fg = min(n_fg, max(1, n // 5))
        n_bg = n - n_fg
        criteria_list = ["basegame"] * n_bg + ["freegame"] * n_fg
        rng = random.Random(101 + seed_off * 17)
        rng.shuffle(criteria_list)
    else:
        criteria_list = [MODE_CRITERIA[mode]] * n
        n_fg = 0
        n_bg = n

    payouts: list[float] = []
    weights: list[float] = []
    hits = 0
    profits = 0
    max_paid = 0.0
    over_cap = 0
    fg_count = 0

    if mode in ("base", "base_ante") and n_fg > 0 and n_bg > 0:
        w_bg = 1.0
        fg_total = quota * n_bg / max(1e-9, 1.0 - quota)
        w_fg = fg_total / n_fg
    else:
        w_bg = 1.0
        w_fg = 1.0

    for i, criteria in enumerate(criteria_list):
        gs = GameState(config)
        gs.betmode = mode
        gs.criteria = criteria
        with contextlib.redirect_stdout(sink):
            gs.run_spin(i + seed_off * 1_000_003)
        pay = float(gs.book.payout_multiplier)
        is_fg = _is_freegame_book(gs)
        if is_fg:
            fg_count += 1
        w = w_fg if is_fg else w_bg
        payouts.append(pay)
        weights.append(w)
        if pay > 0:
            hits += 1
        if pay > cost:
            profits += 1
        if pay > max_paid:
            max_paid = pay
        if pay > config.wincap + 1e-6:
            over_cap += 1

    w_sum = sum(weights) or 1.0
    mean_pay = sum(p * w for p, w in zip(payouts, weights)) / w_sum
    rtp = mean_pay / cost if cost else 0.0
    return {
        "mode": mode,
        "cost": cost,
        "n": n,
        "freegame_books": fg_count,
        "mean_payout": round(mean_pay, 4),
        "rtp": round(rtp, 6),
        "rtp_pct": round(rtp * 100, 3),
        "hit_rate_pct": round(100.0 * hits / n, 2) if n else 0.0,
        "profit_rate_pct": round(100.0 * profits / n, 2) if n else 0.0,
        "max_paid": round(max_paid, 4),
        "over_wincap": over_cap,
        "within_tol": abs(rtp - TARGET_RTP) <= RTP_TOLERANCE,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Monkey Mayhem long RTP audit")
    parser.add_argument("--quick", action="store_true", help="Small N for smoke")
    parser.add_argument("--buys", type=int, default=10_000, help="Buy / feature sample size")
    parser.add_argument("--base", type=int, default=25_000, help="Base / ante sample size")
    parser.add_argument("--mode", choices=list(MODE_COST), help="Single mode only")
    parser.add_argument("--json-out", type=str, default="", help="Write JSON report path")
    args = parser.parse_args()

    if args.quick:
        n_map = {m: 200 for m in MODE_COST}
        n_map["base"] = 800
        n_map["base_ante"] = 800
        n_map["feature_spin"] = 400
        n_map["bonus_see"] = 400
        n_map["bonus_hear"] = 400
    else:
        n_map = {
            "base": args.base,
            "base_ante": args.base,
            "feature_spin": args.buys,
            "bonus_see": args.buys,
            "bonus_hear": args.buys,
        }

    config = fresh_config()
    assert all(v == 1.0 for v in config.coin_tile_scale_by_mode.values())
    assert config.paytable_scale == 1.0
    assert config.bonus_cluster_pay_scale == 1.0
    print(
        f"target={TARGET_RTP} paytable_scale={config.paytable_scale} "
        f"bonus_cluster_pay_scale={config.bonus_cluster_pay_scale} "
        f"caps={config.max_activation_coins_by_mode}"
    )
    print("---")

    modes = [args.mode] if args.mode else list(MODE_COST)
    results = []
    for mode in modes:
        r = audit_mode(mode, n_map[mode], config=config)
        results.append(r)
        print(
            f"{r['mode']:14s} n={r['n']:6d}  RTP={r['rtp_pct']:7.3f}%  "
            f"hit={r['hit_rate_pct']:6.2f}%  profit={r['profit_rate_pct']:6.2f}%  "
            f"fg={r['freegame_books']:4d}  max={r['max_paid']:.2f}  over_cap={r['over_wincap']}  "
            f"{'OK' if r['within_tol'] else 'OFF'}"
        )

    if args.json_out:
        path = Path(args.json_out)
        path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
