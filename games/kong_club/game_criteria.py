"""Stake-brief criteria buckets mapped onto existing MM BetMode names.

Brief role → repo name (do not rename modes):
  ante → base_ante (cost 1.4)
  feature → feature_spin (cost 50)
  summit → peak_spin (cost 1000)
  bonus_3 / bonus_4 / bonus_5 → bonus_see / bonus_hear / bonus_madness
  gamble_scat / gamble_4 / gamble_5 → bonus_gamble / gamble_hear / gamble_madness
"""

from __future__ import annotations

# Feature Spin (50×): always connects, and can reach the 25,000× cap.
FEATURE_DEAD_QUOTA = 0.55
FEATURE_RUN_QUOTA = 0.20
FEATURE_NIBBLE_MAX = 25.0

# TRIFECTA (1000×): dead about 65%. Cap about 1/4000, distinct from every other mode.
PEAK_DEAD_QUOTA = 0.65
PEAK_NIBBLE_QUOTA = 0.20
PEAK_RUN_QUOTA = 0.10
PEAK_CLIP_QUOTA = 0.04
PEAK_TEASE_QUOTA = 0.00975
PEAK_CAP_QUOTA = 0.00025

BASE_CAP_QUOTA = 1 / 1_000_000
ANTE_CAP_QUOTA = 1 / 700_000
FEATURE_CAP_QUOTA = 1 / 80_000
SEE_CAP_QUOTA = 1 / 40_000
HEAR_CAP_QUOTA = 1 / 20_000
GAMBLE_CAP_QUOTA = 1 / 4_500
FEATURE_NIBBLE_QUOTA = 1.0 - FEATURE_DEAD_QUOTA - FEATURE_RUN_QUOTA - FEATURE_CAP_QUOTA
# Brief 10–80 / 80–500 assumes a single toy, not 30 gold virtual coins.
# PEAK lights every cell gold; a connect pays ~30× gold faces (min ~750).
PEAK_NIBBLE = (1.0, 2000.0)
PEAK_RUN = (2000.0, 8000.0)
PEAK_CLIP = (8000.0, 16000.0)
PEAK_TEASE = (16000.0, 24999.0)

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
