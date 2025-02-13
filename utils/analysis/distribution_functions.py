from collections import defaultdict
from math import sqrt
import numpy as np


def get_lookup_length(filepath: str) -> int:
    """Get length of lookup table."""
    return sum(1 for _ in open(filepath, "rb"))


def make_win_distribution(filepath: str, normalize: bool = True) -> dict:
    """Construct win-distribution with unique, ordered payouts."""
    dist = defaultdict(float)
    with open(filepath, "r", encoding="UTF-8") as f:
        for line in f:
            _, weight, payout = line.strip().split(",")
            weight = int(weight)
            payout = float(payout)
            dist[payout] += weight

    # Sort by win amount
    dist = dict(sorted(dist.items(), key=lambda x: x[0], reverse=False))
    if normalize:
        total_weight = sum(dist.values())
        dist = {x: y / total_weight for x, y in dist.items()}

    return dist


def get_distribution_average(dist: dict) -> float:
    """Return weighted average from ordered win distribution."""
    return np.average(list(dist.keys()), weights=list(dist.values()))


def get_distribution_std(filename: str) -> float:
    dist = make_win_distribution(filename)
    av = get_distribution_average(dist)
    win_amounts = np.array(list(dist.keys()))
    probabilities = np.array(list(dist.values()))

    variance = np.average((win_amounts - av) ** 2, weights=probabilities)  # Weighted variance
    return sqrt(variance)


def get_distribution_median(dist: dict) -> float:
    return list(dist.keys())[int(round(len(dist) / 2))]
