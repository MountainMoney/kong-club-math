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
FEATURE_DEAD_QUOTA = 0.0
FEATURE_RUN_QUOTA = 0.375
FEATURE_NIBBLE_MAX = 25.0

# PEAK / summit (1000×): cap ~1/5000 of books.
PEAK_DEAD_QUOTA = 0.50
PEAK_NIBBLE_QUOTA = 0.28
PEAK_RUN_QUOTA = 0.16
PEAK_CLIP_QUOTA = 0.055
PEAK_TEASE_QUOTA = 0.0048
PEAK_CAP_QUOTA = 0.0002
# Brief 10–80 / 80–500 assumes a single toy, not 30 gold virtual coins.
# PEAK lights every cell gold; a connect pays ~30× gold faces (min ~750).
PEAK_NIBBLE = (1.0, 2000.0)
PEAK_RUN = (2000.0, 8000.0)
PEAK_CLIP = (8000.0, 16000.0)
PEAK_TEASE = (16000.0, 24999.0)

# Base cap: 25k at 1/250000 ≈ 10 RTP points. Feature uses the same cap book.
BASE_CAP_QUOTA = 1 / 250_000
FEATURE_CAP_QUOTA = BASE_CAP_QUOTA
FEATURE_NIBBLE_QUOTA = 0.625 - FEATURE_CAP_QUOTA

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
        # Gold-board coins cannot hit the brief's 10–80 band; accept a real connect.
        return tumbles >= 1 and pay > 0
    if bucket == "cap":
        return abs(pay - wincap) < 1e-6
    return True
