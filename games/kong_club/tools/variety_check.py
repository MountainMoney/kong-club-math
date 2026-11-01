#!/usr/bin/env python3
"""Weighted variety report for Kong Club books.

Usage:
  python variety_check.py <publish_files dir>

Reads index.json, lookUpTable_<mode>_0.csv, and books_<mode>.jsonl.zst.
Writes reports/variety_report.md next to the game folder.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import zstandard


def read_lut(path: Path) -> dict[int, int]:
    weights: dict[int, int] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split(",")
            if len(parts) < 3 or not parts[0].strip().lstrip("-").isdigit():
                continue
            book_id = int(parts[0])
            weight = int(parts[1])
            if weight <= 0:
                continue
            weights[book_id] = weights.get(book_id, 0) + weight
    return weights


def iter_books(path: Path):
    with path.open("rb") as handle:
        reader = zstandard.ZstdDecompressor().stream_reader(handle)
        text = io.TextIOWrapper(reader, encoding="utf-8")
        for line in text:
            line = line.strip()
            if line:
                yield json.loads(line)


def payout_band(payout_x: float) -> str:
    edges = [0, 1, 5, 20, 100, 1000, 25000]
    for lo, hi in zip(edges, edges[1:]):
        if payout_x < hi:
            return f"{lo}-{hi}"
    return "25000+"


def size_bucket(size: int) -> str:
    if size < 8:
        return str(size)
    if size < 13:
        return "8-12"
    return "13+"


def signature(book: dict) -> tuple:
    events = book.get("events") or []
    parts = []
    tumbles = 0
    bar = None
    scatters = 0
    reruns = 0
    pots = 0
    clovers = 0
    for event in events:
        kind = event.get("type")
        if kind == "winInfo":
            wins = event.get("wins") or []
            tumbles += 1
            for win in wins:
                parts.append(("win", win.get("symbol"), size_bucket(int(win.get("clusterSize") or 0))))
        elif kind == "progressFill":
            bar = int(event.get("value") or 0)
        elif kind == "boardActivation":
            feature = event.get("coinFeature") or {}
            reruns = int(feature.get("rounds") or 0)
            items = feature.get("items") or []
            pots = sum(1 for item in items if item.get("kind") == "pot")
            clovers = sum(1 for item in items if item.get("kind") == "clover")
            clover_vals = tuple(sorted(int(item.get("value") or 0) for item in items if item.get("kind") == "clover"))
            parts.append(("coin", pots, clovers, reruns, clover_vals))
        elif kind in ("kongClubMode", "freeSpinTrigger", "updateFreeSpin"):
            parts.append((kind, event.get("state") or event.get("total")))
        elif kind == "reveal":
            board = event.get("board") or []
            scatters += sum(
                1
                for reel in board
                for cell in reel
                if isinstance(cell, dict) and (cell.get("scatter") or cell.get("name") == "ST")
            )
    pay = float(book.get("payoutMultiplier") or 0)
    parts.append(("tumbles", min(tumbles, 10)))
    parts.append(("bar", bar))
    parts.append(("scatters", min(scatters, 6)))
    parts.append(("pay", payout_band(pay)))
    return tuple(parts)


def book_features(book: dict) -> dict:
    events = book.get("events") or []
    tumbles = 0
    bar_max = 0
    activated = False
    reruns = 0
    pots = 0
    clovers = 0
    clover_values = []
    cap = False
    reel_sets = []
    spin_wins = []
    current_spin = 0
    total_spins = 0
    mode_state = ""
    for event in events:
        kind = event.get("type")
        if kind == "winInfo":
            tumbles += 1
        elif kind == "progressFill":
            bar_max = max(bar_max, int(event.get("value") or 0))
        elif kind == "boardActivation":
            activated = True
            feature = event.get("coinFeature") or {}
            reruns = max(reruns, int(feature.get("rounds") or 0))
            items = feature.get("items") or []
            pots += sum(1 for item in items if item.get("kind") in ("pot", "collector"))
            clovers += sum(1 for item in items if item.get("kind") == "clover")
            clover_values.extend(int(item.get("value") or 0) for item in items if item.get("kind") == "clover")
            cap = cap or bool(feature.get("capHit")) or int(feature.get("rounds") or 0) >= 10
        elif kind == "reveal":
            if event.get("reelSet"):
                reel_sets.append(str(event.get("reelSet")))
        elif kind == "updateFreeSpin":
            current_spin = int(event.get("amount") or current_spin)
            total_spins = int(event.get("total") or total_spins)
        elif kind == "setWin":
            spin_wins.append((current_spin, float(event.get("amount") or 0)))
        elif kind == "kongClubMode" and not mode_state:
            mode_state = str(event.get("state") or "")
    scatters = 0
    for event in events:
        if event.get("type") != "reveal":
            continue
        for reel in event.get("board") or []:
            for cell in reel:
                if isinstance(cell, dict) and (cell.get("scatter") or cell.get("name") == "ST"):
                    scatters += 1
    arc = ""
    if total_spins and spin_wins:
        best_spin, _best_pay = max(spin_wins, key=lambda item: item[1])
        if best_spin <= total_spins / 3:
            arc = "early"
        elif best_spin > 2 * total_spins / 3:
            arc = "late"
        else:
            arc = "mid"
    return {
        "tumbles": tumbles,
        "bar": 5 if activated else bar_max,
        "activated": activated,
        "reruns": reruns,
        "pots": pots,
        "clovers": clovers,
        "clover_values": clover_values,
        "cap": cap,
        "scatters": scatters,
        "pay": float(book.get("payoutMultiplier") or 0),
        "reel": reel_sets[0] if reel_sets else "",
        "arc": arc,
        "mode_state": mode_state,
    }


def weighted_share(counter: Counter, total: float) -> list[tuple]:
    return sorted(((key, count / total) for key, count in counter.items()), key=lambda item: -item[1])


def _rate(part: float, whole: float) -> float:
    return part / whole if whole else 0.0


def main(publish: Path) -> None:
    index = json.loads((publish / "index.json").read_text(encoding="utf-8"))
    lines = ["# Kong Club variety report", ""]
    lines.append(
        "| mode | strip sets | unique sig | top sig | top-10 | eff books | dups | tumble 3+ / 8+ | bar 3-4 | coin-only / clover / 3+ pots / 5+ reruns | arcs e/m/l | gaps |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|---:|---|---|---|")
    for mode in index["modes"]:
        name = mode["name"]
        lut_path = publish / f"lookUpTable_{name}_0.csv"
        book_path = publish / f"books_{name}.jsonl.zst"
        if not lut_path.exists() or not book_path.exists():
            lines.append(f"| {name} | missing | | | | | | | | | | |")
            continue
        weights = read_lut(lut_path)
        total_w = float(sum(weights.values()) or 1)
        sig_w: Counter = Counter()
        dup_hash: Counter = Counter()
        reel_w: Counter = Counter()
        heavy = []
        win_w = 0.0
        win_books = 0
        books = 0
        tumble3 = tumble8 = 0.0
        bar34 = 0.0
        scat2 = 0.0
        cap_books = 0
        coin_w = coin_only = clover_heavy = pots3 = rerun5 = 0.0
        clover_counts: Counter = Counter()
        arc_w: Counter = Counter()
        bonus_w = 0.0
        state_w: Counter = Counter()
        hit_pays: list[tuple[float, float]] = []
        big_w = big_dup = 0.0
        for book in iter_books(book_path):
            books += 1
            book_id = int(book.get("id", books - 1))
            weight = weights.get(book_id, 0)
            if weight <= 0:
                continue
            feat = book_features(book)
            digest = hashlib.sha1(
                json.dumps(book.get("events"), sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()
            dup_hash[digest] += 1
            if feat["reel"]:
                reel_w[feat["reel"]] += weight
            if feat["cap"]:
                cap_books += 1
            share = weight / total_w
            if feat["tumbles"] >= 3:
                tumble3 += share
            if feat["tumbles"] >= 8:
                tumble8 += share
            if feat["bar"] in (3, 4):
                bar34 += share
            if feat["scatters"] == 2:
                scat2 += share
            if feat["activated"]:
                coin_w += weight
                if feat["pots"] == 0 and feat["clovers"] == 0:
                    coin_only += weight
                if feat["clovers"] >= 3:
                    clover_heavy += weight
                if feat["pots"] >= 3:
                    pots3 += weight
                if max(0, feat["reruns"] - 1) >= 5:
                    rerun5 += weight
                for value in feat["clover_values"]:
                    clover_counts[value] += weight
            if feat["pay"] <= 0:
                continue
            win_books += 1
            win_w += weight
            sig_w[signature(book)] += weight
            heavy.append(weight)
            if name == "peak_spin":
                hit_pays.append((feat["pay"], weight))
            if name in ("bonus_see", "bonus_hear") and feat["arc"]:
                arc_w[feat["arc"]] += weight
                bonus_w += weight
            if feat["mode_state"].startswith("organic_bonus"):
                state_w[feat["mode_state"]] += weight
            if name in ("base", "base_ante") and feat["pay"] >= 1000:
                big_w += 1
        dup_ids = {digest for digest, count in dup_hash.items() if count > 1}
        # Second pass is unnecessary: count duplicate books from the hash counter.
        dups = sum(count for count in dup_hash.values() if count > 1)
        win_w = win_w or 1.0
        top = weighted_share(sig_w, win_w)
        top_sig = top[0][1] if top else 0.0
        heavy.sort(reverse=True)
        top10 = sum(heavy[:10]) / win_w
        probs = [w / win_w for w in sig_w.values()]
        eff = 1 / sum(p * p for p in probs) if probs else 0.0
        coin_w = coin_w or 1.0
        gaps = []
        if name in ("base", "base_ante"):
            if top_sig > 0.03:
                gaps.append(f"top sig {top_sig:.1%}")
            if top10 > 0.10:
                gaps.append(f"top10 {top10:.1%}")
            if tumble3 < 0.08:
                gaps.append(f"tumble3 {tumble3:.1%}")
            if tumble8 < 1 / 2000:
                gaps.append(f"tumble8 1/{1/tumble8:.0f}" if tumble8 else "tumble8 0")
            if not 0.08 <= bar34 <= 0.15:
                gaps.append(f"bar34 {bar34:.1%}")
            if not 0.04 <= scat2 <= 0.10:
                gaps.append(f"scat2 {scat2:.1%}")
        elif name in ("feature_spin", "peak_spin"):
            if top_sig > 0.05:
                gaps.append(f"top sig {top_sig:.1%}")
            if top10 > 0.10:
                gaps.append(f"top10 {top10:.1%}")
        else:
            if top_sig > 0.01:
                gaps.append(f"top sig {top_sig:.1%}")
            if top10 > 0.05:
                gaps.append(f"top10 {top10:.1%}")
        if eff < 2000 or (win_books and eff < 0.05 * win_books):
            gaps.append(f"eff {eff:.0f}")
        if name in ("bonus_see", "bonus_hear", "bonus_gamble", "feature_spin", "peak_spin") and dups:
            gaps.append(f"dups {dups}")
        if cap_books:
            gaps.append(f"cap books {cap_books}")
        shapes = (
            f"{_rate(coin_only, coin_w):.0%}/"
            f"{_rate(clover_heavy, coin_w):.0%}/"
            f"{_rate(pots3, coin_w):.0%}/"
            f"{_rate(rerun5, coin_w):.0%}"
        )
        arcs = ""
        if bonus_w:
            arcs = "/".join(f"{_rate(arc_w[key], bonus_w):.0%}" for key in ("early", "mid", "late"))
            for key in ("early", "mid", "late"):
                if _rate(arc_w[key], bonus_w) < 0.15:
                    gaps.append(f"arc {key} {_rate(arc_w[key], bonus_w):.0%}")
        if name == "peak_spin" and hit_pays:
            hit_w = sum(weight for _, weight in hit_pays) or 1.0
            by_pay: Counter = Counter()
            for pay, weight in hit_pays:
                by_pay[pay] += weight
            if max(by_pay.values()) / hit_w > 0.10:
                gaps.append("one peak pay >10%")
            mean = sum(pay * weight for pay, weight in hit_pays) / hit_w
            var = sum(weight * (pay - mean) ** 2 for pay, weight in hit_pays) / hit_w
            cv = (var ** 0.5) / mean if mean else 0.0
            if cv < 0.5:
                gaps.append(f"cv {cv:.2f}")
        reel_txt = ",".join(f"{key}:{value/total_w:.0%}" for key, value in reel_w.most_common())
        lines.append(
            f"| {name} | {len(reel_w)} | {len(sig_w)} | {top_sig:.1%} | {top10:.1%} | {eff:.0f} | {dups} | "
            f"{tumble3:.1%} / {tumble8:.2%} | {bar34:.1%} | {shapes} | {arcs} | {', '.join(gaps) or 'ok'} |"
        )
        lines.append("")
        lines.append(f"<!-- {name} reels {reel_txt} -->")
        if state_w:
            lines.append(
                "<!-- "
                + name
                + " bonus split "
                + ", ".join(f"{key}:{value/total_w:.4%}" for key, value in state_w.most_common())
                + " -->"
            )
        if clover_counts:
            clover_total = sum(clover_counts.values()) or 1
            mix = ", ".join(
                f"{key}:{clover_counts[key]/clover_total:.1%}" for key in sorted(clover_counts)
            )
            lines.append(f"<!-- {name} clovers {mix} -->")
        lines.append(f"<!-- {name} scatters==2 {scat2:.2%} big10x books {big_w:.0f} -->")
    out = Path(__file__).resolve().parents[1] / "reports" / "variety_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
