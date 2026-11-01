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
    tumbles = sum(1 for event in events if event.get("type") == "winInfo")
    bar = 0
    reruns = 0
    pots = 0
    clovers = 0
    clover_values = []
    cap = False
    for event in events:
        if event.get("type") == "progressFill":
            bar = int(event.get("value") or 0)
        if event.get("type") == "boardActivation":
            feature = event.get("coinFeature") or {}
            reruns = int(feature.get("rounds") or 0)
            items = feature.get("items") or []
            pots = sum(1 for item in items if item.get("kind") == "pot")
            clovers = sum(1 for item in items if item.get("kind") == "clover")
            clover_values = [int(item.get("value") or 0) for item in items if item.get("kind") == "clover"]
            cap = bool(feature.get("capHit")) or reruns >= 10
    scatters = 0
    for event in events:
        if event.get("type") != "reveal":
            continue
        for reel in event.get("board") or []:
            for cell in reel:
                if isinstance(cell, dict) and (cell.get("scatter") or cell.get("name") == "ST"):
                    scatters += 1
    return {
        "tumbles": tumbles,
        "bar": bar,
        "reruns": reruns,
        "pots": pots,
        "clovers": clovers,
        "clover_values": clover_values,
        "cap": cap,
        "scatters": scatters,
        "pay": float(book.get("payoutMultiplier") or 0),
    }


def weighted_share(counter: Counter, total: float) -> list[tuple]:
    return sorted(((key, count / total) for key, count in counter.items()), key=lambda item: -item[1])


def main(publish: Path) -> None:
    index = json.loads((publish / "index.json").read_text(encoding="utf-8"))
    lines = ["# Kong Club variety report", ""]
    for mode in index["modes"]:
        name = mode["name"]
        lut_path = publish / f"lookUpTable_{name}_0.csv"
        book_path = publish / f"books_{name}.jsonl.zst"
        if not lut_path.exists() or not book_path.exists():
            lines.append(f"## {name}\nmissing books or lut\n")
            continue
        weights = read_lut(lut_path)
        total_w = sum(weights.values()) or 1
        sig_w = Counter()
        dup_hash = Counter()
        win_w = 0.0
        heavy = []
        tumble_w = Counter()
        bar_w = Counter()
        rerun_w = Counter()
        cap_w = 0.0
        books = 0
        win_books = 0
        for book in iter_books(book_path):
            books += 1
            book_id = int(book.get("id", books - 1))
            weight = weights.get(book_id, 0)
            if weight <= 0:
                continue
            feat = book_features(book)
            raw = json.dumps(book.get("events"), sort_keys=True, default=str)
            dup_hash[hashlib.sha1(raw.encode("utf-8")).hexdigest()] += 1
            if feat["pay"] <= 0:
                continue
            win_books += 1
            win_w += weight
            sig_w[signature(book)] += weight
            heavy.append(weight)
            tumble_w[min(feat["tumbles"], 10)] += weight
            bar_w[min(feat["bar"], 5)] += weight
            rerun_w[min(feat["reruns"], 10)] += weight
            if feat["cap"]:
                cap_w += weight
        win_w = win_w or 1
        top = weighted_share(sig_w, win_w)
        heavy.sort(reverse=True)
        top10 = sum(heavy[:10]) / win_w
        probs = [w / win_w for w in sig_w.values()]
        eff = 1 / sum(p * p for p in probs) if probs else 0
        dups = sum(1 for count in dup_hash.values() if count > 1)
        lines.append(f"## {name}")
        lines.append(f"- books {books}, winning books {win_books}")
        lines.append(f"- unique signatures {len(sig_w)}")
        lines.append(f"- top signature share {top[0][1] if top else 0:.4%}")
        lines.append(f"- top-10 book share {top10:.4%}")
        lines.append(f"- effective books {eff:.1f}")
        lines.append(f"- duplicate event-list hashes {dups}")
        lines.append(f"- tumble weights {dict(sorted(tumble_w.items()))}")
        lines.append(f"- bar weights {dict(sorted(bar_w.items()))}")
        lines.append(f"- rerun weights {dict(sorted(rerun_w.items()))}")
        lines.append(f"- rerun-cap weight share {cap_w / win_w:.6%}")
        lines.append("")
    out = Path(__file__).resolve().parents[1] / "reports" / "variety_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
