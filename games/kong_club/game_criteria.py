"""Stake criteria for the 2026-11-04 locked spec.

Ante is base_ante at 1.4x. Hunt stops are ante-style modes (hunt_2..hunt_5).
Feature Spin is feature_spin. Trifecta is peak_spin. Direct buys are
bonus_see / bonus_hear. Mystery is bonus_mystery (50/45/5 See/Hear/Speak).
Risky Mystery is bonus_risky (50% dead / 40% Hear / 10% Speak).
Speak No Evil is the variant name `speak` (formerly Madness).
"""

from __future__ import annotations

# Feature Spin: every spin connects. No dead bucket. Price is re-solved.
FEATURE_DEAD_QUOTA = 0.0
FEATURE_RUN_QUOTA = 1.0

# Trifecta: 50% dead, 50% all-gold connect + one coin game.
PEAK_DEAD_QUOTA = 0.50
PEAK_LIVE_QUOTA = 0.50

# Forced max-win books are omitted at 500 sims. A 1-in-a-million cap quota
# still reserves a book under the sim splitter and would dominate RTP.
BASE_CAP_QUOTA = 0.0
ANTE_CAP_QUOTA = 0.0
FEATURE_CAP_QUOTA = 0.0
SEE_CAP_QUOTA = 0.0
HEAR_CAP_QUOTA = 0.0
GAMBLE_CAP_QUOTA = 0.0

# Ante identity at 96.3%: base freegame 1/260, ante exactly twice that, cost 1.4.
# S + p*(F-S) = 0.963 and S + 2p*(F-S) = 1.4*0.963, with p = 1/260.
TARGET_RTP = 0.963
TARGET_BASE_SPIN_EV = 0.5778
# E[freegame] - S. Ante stays at twice the base trigger rate.
# Gap is refreshed from the See-heavy sample (gold-lean coin games).
TARGET_BONUS_GAP = 200.0
SPEAK_DIRECT_MIN_WIN = 1000.0

# Mystery Bonus: guaranteed 50% See / 45% Hear / 5% Speak.
MYSTERY_SEE_QUOTA = 0.50
MYSTERY_HEAR_QUOTA = 0.45
MYSTERY_SPEAK_QUOTA = 0.05
# Risky Mystery: 50% dead / 40% Hear / 10% Speak.
RISKY_DEAD_QUOTA = 0.50
RISKY_HEAR_QUOTA = 0.40
RISKY_SPEAK_QUOTA = 0.10

# Hunt slider (locked spec l.38; mode_spec 2026-11-03 "Hunt L1-4 locked"). Each stop
# is written "Nx a/b/c": the spin costs N x bet, and the See / Hear / Speak trigger
# odds are a / b / c times the base game's. Hunt boosts scatters only, not the coin
# game. The five stops map 1:1 onto hunt_2..hunt_6 (hunt_6 = L5).
# L1 follows the locked spec (3/5/10); mode_spec 2026-11-03 wrote 3/3/5.
# Option (a), Ryan 2026-11-09, with the integer rule (10:02): See boosts 3/5/7/9 (the 8.5 was
# the 5x stop's See, raised to 9); Hear/Speak are the whole-number roundings of the smallest
# change that lands each stop on 96.3% (proposed 5/10, 6/10, 10/18, 15/30). The last few
# hundredths of a point are closed by each stop's bar-fill pace in scripts/fit_rebalance.py.
# hunt_6 = Hunt L5 (added 2026-11-09): spec boosts See 32 / Hear 210 / Speak 420 kept,
# price solved to a whole 18x (17x would need a negative bar pace).
HUNT_LEVELS = {
    "hunt_2": {"cost": 2.0, "boost": {"see": 3, "hear": 4, "speak": 7}},
    "hunt_3": {"cost": 3.0, "boost": {"see": 5, "hear": 10, "speak": 13}},
    "hunt_4": {"cost": 4.0, "boost": {"see": 7, "hear": 10, "speak": 18}},
    "hunt_5": {"cost": 5.0, "boost": {"see": 9, "hear": 15, "speak": 30}},
    "hunt_6": {"cost": 18.0, "boost": {"see": 32, "hear": 210, "speak": 420}},
}
HUNT_COSTS = {name: level["cost"] for name, level in HUNT_LEVELS.items()}
SCATTER_COUNT_VARIANT = {3: "see", 4: "hear", 5: "speak"}


def hunt_scatter_triggers(base_triggers: dict[int, float], mode: str) -> dict[int, float]:
    """Base scatter-count mix with each bonus type scaled by its Hunt boost."""
    boost = HUNT_LEVELS[mode]["boost"]
    return {
        count: float(weight) * boost[SCATTER_COUNT_VARIANT.get(count, "speak")]
        for count, weight in base_triggers.items()
    }


def hunt_odds_factor(base_triggers: dict[int, float], mode: str) -> float:
    """Overall bonus-odds multiplier vs base: the boosts weighted by the base mix."""
    total = float(sum(base_triggers.values())) or 1.0
    return sum(hunt_scatter_triggers(base_triggers, mode).values()) / total


def hunt_freegame_quota(cost: float) -> float:
    """Bonus rate that keeps a hunt stop on the ante identity (same S and F)."""
    quota = (TARGET_RTP * float(cost) - TARGET_BASE_SPIN_EV) / TARGET_BONUS_GAP
    return max(0.002, min(0.85, quota))

LEGACY_FEATURE = "feature_spin"
LEGACY_PEAK = "peak_spin"


def normalize_bucket(betmode: str, criteria: str) -> str:
    """Map leftover single-mode criteria onto the default live bucket."""
    if betmode == "feature_spin" and criteria in (LEGACY_FEATURE, "", None):
        return "run"
    if betmode == "peak_spin" and criteria in (LEGACY_PEAK, "", None):
        return "nibble"
    return criteria or ""


def payout_in_range(pay: float, lo: float, hi: float) -> bool:
    return lo - 1e-6 <= pay <= hi + 1e-6


def feature_bucket_ok(bucket: str, pay: float, tumbles: int) -> bool:
    if bucket == "dead_juicy":
        return pay <= 1e-9 and tumbles <= 0
    if bucket == "cap":
        return True
    if bucket in ("nibble", "run"):
        return tumbles >= 1 and pay > 0
    return True


def peak_bucket_ok(bucket: str, pay: float, tumbles: int, wincap: float) -> bool:
    if bucket == "dead_juicy":
        return pay <= 1e-9 and tumbles <= 0
    if bucket in ("nibble", "run", "clip", "tease"):
        return pay > 0
    if bucket == "cap":
        return abs(pay - wincap) < 1e-6
    return True
