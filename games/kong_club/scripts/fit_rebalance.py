"""Plain-pay rebalance: lookup weights from design odds, not from reshaping big books.

Every book belongs to a class (plain spin, bar fill, See / Hear / Speak bonus, ...).
A class's probability comes from the design below. Organic bonuses (base, Ante, Hunt)
and bought bonuses are separate classes. Inside a class every book starts
with the same weight; a mild calibration (books on one side of the class mean lose at
most MAX_TILT of their weight, never gained by single books) moves each mode's sample
to the pooled class mean measured over all modes, so every mode prices the same game.

Design (levers, in order of preference already applied in game_config):
  * Base See / Hear / Speak trigger odds: chosen so the locked Hunt grid (costs 2/3/4/5,
    boosts 3/5/10, 5/6/10, 7/10/18, 8.5/15/30) lands as close to 96.3% as it can.
  * Base bar-fill rate: solved so base returns 96.3% (plain cluster pay is locked).
  * Ante (1.4x): one odds multiplier on all bonus types, solved to 96.3%.
  * Hunt: base odds x boosts, bar rate as base. RTP is reported, never forced.
  * Buys / Feature / Trifecta: price = class EV / 0.963 (rounded), then calibrated.
Usage: fit_rebalance.py [--write]   (without --write: report only)
"""

from __future__ import annotations

import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import zstandard

GAME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GAME))
from game_criteria import HUNT_LEVELS  # noqa: E402

PUBLISH = GAME / "library" / "publish_files"
TARGET = 0.963
TOTAL = 10**12
MAX_TILT = 0.5
WINCAP = 25000.0
ANTE_COST = 1.4
BASE_LIKE = ["base", "base_ante", *HUNT_LEVELS]
# Search box for organic Hear / Speak odds in base (1 in N spins).
HEAR_ONE_IN = (20_000, 100_000)
SPEAK_ONE_IN = (200_000, 2_000_000)
# The locked grid cannot put all four stops on 96.3% at once (5x has See 8.5, below
# the 2*cost-1 = 9 the first three stops follow). The base odds are fitted to 2x-4x;
# 5x is reported with its gap.
DESIGN_LEVELS = ("hunt_2", "hunt_3", "hunt_4")


def read_books(mode: str) -> list[dict]:
    path = PUBLISH / f"books_{mode}.jsonl.zst"
    with path.open("rb") as handle:
        text = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(handle), encoding="utf-8")
        return [json.loads(line) for line in text if line.strip()]


def entry_variant(book: dict) -> str:
    for event in book.get("events", []):
        if event.get("type") == "kongClubMode":
            state = str(event.get("state") or "")
            for variant in ("see", "hear", "speak"):
                if state.endswith(variant):
                    return variant
    raise ValueError(f"book {book.get('id')} has no bonus entry state")


def book_class(mode: str, book: dict) -> str:
    crit = str(book.get("criteria") or "")
    if mode in BASE_LIKE:
        if crit == "freegame":
            return entry_variant(book)
        return {"basegame": "plain", "bar_pay": "bar"}[crit]
    if mode == "bonus_see":
        return "see"
    if mode == "bonus_hear":
        return "hear"
    if mode == "bonus_mystery":
        return crit.replace("pick_", "")
    if mode == "bonus_risky":
        return {"risky_dead": "dead", "risky_hear": "hear", "risky_speak": "speak"}[crit]
    if mode == "feature_spin":
        return "feature"
    if mode == "peak_spin":
        return {"dead_juicy": "dead", "live": "live"}[crit]
    raise ValueError(mode)


def mean(values):
    return sum(values) / len(values) if values else 0.0


def calibrate(pays: list[float], target: float) -> tuple[list[float], float, bool]:
    """Relative weights with weighted mean = target. Books below (or above) the class
    mean lose up to MAX_TILT of their weight; no single book is pushed up."""
    m = mean(pays)
    if abs(target - m) <= 1e-12 * max(1.0, abs(m)):
        return [1.0] * len(pays), 0.0, True
    side_low = target > m
    pick = [(p < m) if side_low else (p > m) for p in pays]

    def wmean(alpha):
        w = [(1 - alpha) if s else 1.0 for s in pick]
        return sum(a * b for a, b in zip(w, pays)) / sum(w)

    lo, hi = 0.0, MAX_TILT
    ok = (wmean(hi) >= target) if side_low else (wmean(hi) <= target)
    if not ok:
        return [(1 - hi) if s else 1.0 for s in pick], hi, False
    for _ in range(100):
        mid = (lo + hi) / 2
        if (wmean(mid) < target) == side_low:
            lo = mid
        else:
            hi = mid
    alpha = (lo + hi) / 2
    return [(1 - alpha) if s else 1.0 for s in pick], alpha, True


def build_rows(classes, probs, targets):
    """classes: {cls: [(id, pay_cents)]}; probs: {cls: p}; targets: {cls: mean x}."""
    rows, notes, clean = [], {}, True
    for cls, members in classes.items():
        p = probs.get(cls, 0.0)
        if p <= 0:
            # Book kept with weight 1 so the file stays complete; ~0 probability.
            rows += [(sid, 1, pay) for sid, pay in members]
            continue
        pays = [pay / 100 for _sid, pay in members]
        rel, alpha, ok = calibrate(pays, targets[cls]) if cls in targets else ([1.0] * len(pays), 0.0, True)
        clean &= ok
        achieved = sum(a * b for a, b in zip(rel, pays)) / sum(rel)
        notes[cls] = {"n": len(members), "p": p, "sample_mean": mean(pays), "target": targets.get(cls),
                      "achieved": achieved, "tilt": round(alpha, 4), "ok": ok}
        s = sum(rel)
        rows += [(sid, max(1, round(p * TOTAL * w / s)), pay) for (sid, pay), w in zip(members, rel)]
    for cls in probs:
        if probs[cls] > 0 and cls not in classes:
            clean = False
            notes[cls] = {"n": 0, "p": probs[cls], "ok": False, "missing": True}
    return rows, notes, clean


def stats(rows, cost):
    W = sum(w for _s, w, _p in rows)
    ev = sum(w * p for _s, w, p in rows) / W / 100
    share = lambda t: (sum(w * p for _s, w, p in rows if p / 100 > t) / W / 100) / ev if ev else 0.0
    return {
        "cost": cost,
        "rtp": ev / cost,
        "hit": sum(w for _s, w, p in rows if p > 0) / W,
        "max_win": max(p for *_r, p in rows) / 100,
        "share_gt_100x": share(100),
        "share_gt_1000x": share(1000),
        "share_gt_5000x": share(5000),
        "ess": W * W / sum(w * w for _s, w, _p in rows),
        "books": len(rows),
        "cap_books": sum(1 for *_r, p in rows if p >= WINCAP * 100),
    }


def solve_design(E):
    """Base odds by type: minimise the worst miss over DESIGN_LEVELS inside the box."""
    best = None
    for hear_n in range(HEAR_ONE_IN[0], HEAR_ONE_IN[1] + 1, 2_000):
        for speak_n in range(SPEAK_ONE_IN[0], SPEAK_ONE_IN[1] + 1, 50_000):
            ch, ck = E["hear"] / hear_n, E["speak"] / speak_n
            for i in range(0, 2001):
                cs = 0.2 + i * 0.0002
                worst = 0.0
                for name in DESIGN_LEVELS:
                    lvl = HUNT_LEVELS[name]
                    b, c = lvl["boost"], lvl["cost"]
                    rtp = (TARGET + (b["see"] - 1) * cs + (b["hear"] - 1) * ch + (b["speak"] - 1) * ck) / c
                    worst = max(worst, abs(rtp - TARGET))
                if best is None or worst < best[0] - 1e-12:
                    best = (worst, cs, hear_n, speak_n)
    _w, cs, hear_n, speak_n = best
    q = {"see": cs / E["see"], "hear": 1 / hear_n, "speak": 1 / speak_n}
    return q


def main(write: bool) -> None:
    modes = [m["name"] for m in json.loads((PUBLISH / "index.json").read_text())["modes"]]
    books = {m: read_books(m) for m in modes}
    classes = {m: defaultdict(list) for m in modes}
    pooled = defaultdict(list)
    for m in modes:
        for b in books[m]:
            cls = book_class(m, b)
            classes[m][cls].append((int(b["id"]), int(b["payoutMultiplier"])))
            if cls in ("see", "hear", "speak", "bar", "plain"):
                # Organic bonuses (base-like modes, trigger spin included) and bought
                # bonuses are pooled apart: they are not the same payout distribution.
                key = cls if (m in BASE_LIKE or cls not in ("see", "hear", "speak")) else f"buy_{cls}"
                pooled[key].append(int(b["payoutMultiplier"]) / 100)
    E = {k: mean(v) for k, v in pooled.items()}
    E["dead"] = 0.0
    q = solve_design(E)
    Q = sum(q.values())
    bon = sum(q[v] * E[v] for v in q)
    p_bar = (TARGET - bon - (1 - Q) * E["plain"]) / (E["bar"] - E["plain"])
    ante_m = (ANTE_COST * TARGET - p_bar * E["bar"] - (1 - p_bar) * E["plain"]) / (bon - Q * E["plain"])
    design = {"E": E, "pooled_n": {k: len(v) for k, v in pooled.items()}, "base_odds_one_in": {k: 1 / v for k, v in q.items()},
              "bar_one_in": 1 / p_bar if p_bar > 0 else None, "ante_odds_multiplier": ante_m}
    prices = json.loads((GAME / "mode_prices.json").read_text())
    old_prices = dict(prices)
    out = {}
    for m in modes:
        cls = classes[m]
        if m in BASE_LIKE:
            mult = {"base": {v: 1.0 for v in q}, "base_ante": {v: ante_m for v in q}}.get(m) or HUNT_LEVELS[m]["boost"]
            probs = {v: q[v] * mult[v] for v in q}
            probs["bar"] = p_bar
            probs["plain"] = 1 - sum(probs.values())
            targets = {k: E[k] for k in probs}
            cost = {"base": 1.0, "base_ante": ANTE_COST}.get(m) or HUNT_LEVELS[m]["cost"]
        else:
            fixed = {
                "bonus_see": {"see": 1.0},
                "bonus_hear": {"hear": 1.0},
                "bonus_mystery": {"see": 0.5, "hear": 0.45, "speak": 0.05},
                "bonus_risky": {"dead": 0.5, "hear": 0.4, "speak": 0.1},
                "feature_spin": {"feature": 1.0},
                "peak_spin": {"dead": 0.5, "live": 0.5},
            }[m]
            probs = dict(fixed)
            own = {k: mean([p / 100 for _s, p in cls[k]]) for k in cls}
            base_t = {k: (E[f"buy_{k}"] if f"buy_{k}" in E else own[k]) for k in probs}
            ev = sum(probs[k] * base_t[k] for k in probs)
            step = 0.5 if ev / TARGET < 100 else 1.0
            cost = round(ev / TARGET / step) * step
            f = cost * TARGET / ev
            targets = {k: base_t[k] * f for k in probs}
        rows, notes, clean = build_rows(cls, probs, targets)
        if m in ("base", "base_ante"):
            # Classes whose sample could not reach the pooled mean within MAX_TILT keep
            # their achieved mean; the mode's free lever absorbs the difference
            # (base: bar-fill rate, Ante: bonus-odds multiplier).
            A = {k: v["achieved"] for k, v in notes.items()}
            if m == "base":
                bon_a = sum(q[v] * A[v] for v in q)
                p_bar = (TARGET - bon_a - (1 - Q) * A["plain"]) / (A["bar"] - A["plain"])
                probs = {v: q[v] for v in q}
            else:
                bon_a = sum(q[v] * A[v] for v in q)
                ante_m = (ANTE_COST * TARGET - p_bar * A["bar"] - (1 - p_bar) * A["plain"]) / (bon_a - Q * A["plain"])
                probs = {v: q[v] * ante_m for v in q}
            probs["bar"] = p_bar
            probs["plain"] = 1 - sum(probs.values())
            rows, notes, clean = build_rows(cls, probs, targets)
            design["bar_one_in"] = 1 / p_bar
            design["ante_odds_multiplier"] = ante_m
        st = stats(rows, cost)
        # Clean = exactly on target with every class inside the tilt limit. A class that
        # could not reach its pooled mean is listed in "classes" (ok=False).
        st["clean"] = bool(abs(st["rtp"] - TARGET) < 1e-4)
        st["all_classes_at_pooled_mean"] = bool(clean)
        st["old_price"] = old_prices.get(m)
        st["classes"] = notes
        out[m] = st
        prices[m] = cost
        if write and st["clean"]:
            text = "".join(f"{s},{w},{p}\n" for s, w, p in rows)
            for name in (f"lookUpTable_{m}_0.csv", f"lookUpTable_{m}.csv"):
                path = PUBLISH / name
                if name.endswith("_0.csv") or path.exists():
                    path.write_text(text, encoding="utf-8")
    # Hunt: odds per bonus type, design RTP (pooled class means), and the cost that
    # would put each stop on 96.3%. L5 (~25x, See 32 / Hear 210 / Speak 420) has no
    # mode; its solving cost is information only.
    hunt = {}
    levels = dict(HUNT_LEVELS)
    levels["L5_info_only"] = {"cost": 25.0, "boost": {"see": 32.0, "hear": 210.0, "speak": 420.0}}
    for name, lvl in levels.items():
        b = lvl["boost"]
        odds = {v: q[v] * b[v] for v in q}
        ev = (1 - p_bar - sum(odds.values())) * E["plain"] + p_bar * E["bar"] + sum(odds[v] * E[v] for v in q)
        entry = {
            "cost": lvl["cost"],
            "boost": b,
            "odds_one_in": {v: 1 / o for v, o in odds.items()},
            "any_bonus_one_in": 1 / sum(odds.values()),
            "design_rtp": ev / lvl["cost"],
            "cost_for_96_3": ev / TARGET,
        }
        if name in out:
            entry["lut_rtp"] = out[name]["rtp"]
            entry["lut_cost_for_96_3"] = out[name]["rtp"] * lvl["cost"] / TARGET
        hunt[name] = entry
    design["hunt"] = hunt
    report = {"design": design, "modes": out}
    (GAME / "reports").mkdir(exist_ok=True)
    print(json.dumps(design, indent=1))
    print(f"{'mode':14} {'old':>8} {'price':>8} {'RTP%':>8} {'hit%':>6} {'max':>8} {'>100x':>6} {'>1kx':>6} {'>5kx':>6} {'ESS':>6} {'cap':>3} clean")
    for m, s in out.items():
        print(f"{m:14} {s['old_price'] or 0:8.2f} {s['cost']:8.2f} {s['rtp']*100:8.3f} {s['hit']*100:6.2f} {s['max_win']:8.1f} "
              f"{s['share_gt_100x']*100:6.1f} {s['share_gt_1000x']*100:6.1f} {s['share_gt_5000x']*100:6.1f} {s['ess']:6.1f} {s['cap_books']:3d} {s['clean']}")
    if write:
        (GAME / "reports" / "rebalance_2026-11-08.json").write_text(json.dumps(report, indent=1) + "\n")
        clean_prices = {m: (prices[m] if out[m]["clean"] else old_prices.get(m, prices[m])) for m in prices}
        (GAME / "mode_prices.json").write_text(json.dumps(clean_prices, indent=2) + "\n")
        index_path = PUBLISH / "index.json"
        index = json.loads(index_path.read_text())
        for mode in index["modes"]:
            mode["cost"] = clean_prices.get(mode["name"], mode["cost"])
        index_path.write_text(json.dumps(index, indent=4) + "\n")
    else:
        Path("/tmp/rebalance_report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main("--write" in sys.argv)
