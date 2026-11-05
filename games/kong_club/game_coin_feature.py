"""Coin game — lit tiles flip into coins, clovers, and pots, then may rerun.

Flip weights are per tile tier (coin / clover / pot). Clovers fire in reading
order and multiply adjacent coins and valued pots (8-way, not other clovers).
Pots then chain left to right: each collects every coin, and the last pot holds
the total. Collected coins, used clovers, and spent pots flip again. The loop
stops when a round flips no new clover and no new pot. A 10-rerun cap pays the
max win. Tiles themselves never multiply a payout.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_executables import GameExecutables

ADJACENT_8: tuple[tuple[int, int], ...] = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)


def highlighted_positions(gamestate: "GameExecutables") -> list[tuple[int, int]]:
    """Every bronze, silver, or gold tile flips. Plain tiles never flip."""
    positions: list[tuple[int, int]] = []
    for reel in range(gamestate.config.num_reels):
        for row in range(gamestate.config.num_rows[reel]):
            if gamestate.tile_levels[reel][row] <= 0:
                continue
            positions.append((reel, row))
    positions.sort(key=lambda pos: (pos[0], pos[1]))
    return positions


def _virtual_coin_symbol(tile_level: int) -> str:
    """1=bronze/CB, 2=silver/CS, 3=gold/CG."""
    if tile_level <= 1:
        return "CB"
    if tile_level == 2:
        return "CS"
    return "CG"


# Face pools: bronze 1–4, silver 5–20, gold 25+. MULTI faces promote metal when they enter the next band.
_SILVER_FACE_MIN = 5
_GOLD_FACE_MIN = 25


def _coin_metal_for_face(face: int, current_level: int = 1) -> tuple[str, int]:
    """Promote CB→CS→CG when a multiplied face fits the next tier. Never demote."""
    if face >= _GOLD_FACE_MIN:
        level = 3
    elif face >= _SILVER_FACE_MIN:
        level = 2
    else:
        level = 1
    level = max(level, max(int(current_level), 1))
    return _virtual_coin_symbol(level), level


def _pick_weighted_coin_value(
    gamestate: "GameExecutables", tile_level: int, rng: random.Random
) -> int:
    pools = getattr(gamestate.config, "activation_coin_value_pools", {}) or {}
    weights_by_level = getattr(gamestate.config, "activation_coin_value_weights", {}) or {}
    if getattr(gamestate, "betmode", None) == "peak_spin":
        pool = list((getattr(gamestate.config, "coin_values", {}) or {}).get("CG") or [25, 50, 100, 250, 500])
        weights = list(getattr(gamestate.config, "peak_coin_value_weights", None) or [])
        if len(weights) != len(pool):
            weights = [1] * len(pool)
        return int(rng.choices(pool, weights=weights, k=1)[0])
    buy_weights = _buy_coin_weights(gamestate, tile_level)
    if buy_weights is not None:
        pool, weights = buy_weights
        return int(rng.choices(pool, weights=weights, k=1)[0])
    pool = pools.get(tile_level) or pools.get(1) or [1]
    weights = weights_by_level.get(tile_level)
    if not weights or len(weights) != len(pool):
        weights = [1] * len(pool)
    return int(rng.choices(pool, weights=weights, k=1)[0])


def _direct_buy(gamestate: "GameExecutables") -> bool:
    return getattr(gamestate, "betmode", None) in {
        "bonus_see",
        "bonus_hear",
        "bonus_pick",
        "bonus_risky",
    }


def _buy_power_scale(gamestate: "GameExecutables") -> float:
    """Clover/pot rate scale for the priced buys only. Base and the other modes stay put."""
    if not _direct_buy(gamestate):
        return 1.0
    variant = getattr(gamestate, "bonus_variant", None)
    mode = getattr(gamestate, "betmode", None)
    if variant == "speak" and mode == "bonus_pick":
        return float(getattr(gamestate.config, "mystery_speak_power_scale", 1.0) or 1.0)
    if variant == "speak" and mode == "bonus_risky":
        return float(getattr(gamestate.config, "risky_speak_power_scale", 1.0) or 1.0)
    if variant == "hear" or mode == "bonus_hear":
        return float(getattr(gamestate.config, "hear_power_scale", None) or getattr(gamestate.config, "buy_power_scale", 1.0) or 1.0)
    if variant == "see" or mode == "bonus_see":
        return float(getattr(gamestate.config, "see_power_scale", None) or getattr(gamestate.config, "buy_power_scale", 1.0) or 1.0)
    return float(getattr(gamestate.config, "buy_power_scale", 1.0) or 1.0)


def _buy_coin_weights(gamestate: "GameExecutables", tile_level: int):
    if not _direct_buy(gamestate):
        return None
    table = getattr(gamestate.config, "buy_coin_value_weights", None) or {}
    symbol = "CB" if tile_level <= 1 else "CS" if tile_level == 2 else "CG"
    variant = getattr(gamestate, "bonus_variant", None)
    mode = getattr(gamestate, "betmode", None)
    if variant == "speak" and mode == "bonus_pick":
        table = getattr(gamestate.config, "mystery_speak_coin_weights", None) or table
    elif variant == "speak" and mode == "bonus_risky":
        table = getattr(gamestate.config, "risky_speak_coin_weights", None) or table
    weights = table.get(symbol)
    pool = list((getattr(gamestate.config, "coin_values", {}) or {}).get(symbol) or [])
    if not weights or not pool or len(weights) != len(pool):
        return None
    return pool, list(weights)


def _pick_multi_value(gamestate: "GameExecutables", rng: random.Random) -> int:
    values = list(getattr(gamestate.config, "coin_game_multi_values", None) or [2, 3, 4, 5, 10, 20])
    weights = list(getattr(gamestate.config, "coin_game_multi_weights", None) or [1] * len(values))
    if len(weights) != len(values):
        weights = [1] * len(values)
    return int(rng.choices(values, weights=weights, k=1)[0])


def _mode_power_weights(gamestate: "GameExecutables") -> dict[str, int]:
    table = getattr(gamestate.config, "coin_game_power_weights", {}) or {}
    freegame = getattr(gamestate.config, "freegame_type", "freegame")
    if getattr(gamestate, "gametype", None) == freegame:
        variant = getattr(gamestate, "bonus_variant", None)
        if variant in ("hear", "speak", "madness"):
            key = "bonus_speak" if variant in ("speak", "madness") else f"bonus_{variant}"
            if key in table:
                return dict(table[key])
    mode = getattr(gamestate, "betmode", "base")
    if mode in table:
        return dict(table[mode])
    # Extra Chance / unknown modes must not fall to zeros — fallback is bronze rates.
    return dict(table.get("base", {"multiplier": 0, "collector": 0, "tier_shift": 0}))


def _tile_power_weights(gamestate: "GameExecutables", tile_level: int) -> dict[str, int]:
    table = getattr(gamestate.config, "coin_game_power_by_tile_level", {}) or {}
    level = max(1, min(3, int(tile_level or 1)))
    if getattr(gamestate, "betmode", None) == "peak_spin" and level == 3:
        peak = getattr(gamestate.config, "coin_game_power_peak_gold", None)
        if peak:
            return dict(peak)
    profile = table.get(level)
    if profile is None:
        profile = table.get(str(level))
    if profile:
        return dict(profile)
    return _mode_power_weights(gamestate)


def _pick_cell_kind(
    gamestate: "GameExecutables",
    rng: random.Random,
    tile_level: int = 1,
    *,
    reactivate: bool = False,
) -> str:
    """Roll coin vs clover vs pot. Reruns may spawn pots (silver and gold)."""
    # Trifecta reruns are plain coins. The opening board is composed, not rolled.
    if getattr(gamestate, "betmode", None) == "peak_spin":
        return "coin"
    if reactivate:
        table = getattr(gamestate.config, "coin_game_rerun_power_by_tile_level", None) or {}
        level = max(1, min(3, int(tile_level or 1)))
        power = dict(table.get(level) or {"coin": 100, "multiplier": 3, "collector": 0})
        coin_w = int(power.get("coin", 100) or 100)
    else:
        power = _tile_power_weights(gamestate, tile_level)
        coin_w = int(getattr(gamestate.config, "coin_game_coin_weight", 100) or 100)
    labels = ["coin"]
    weights = [max(coin_w, 0)]
    scale = _buy_power_scale(gamestate)
    multi_w = int(round(int(power.get("multiplier", 0) or 0) * scale))
    if multi_w > 0:
        labels.append("multiplier")
        weights.append(multi_w)
    collector_w = int(round(int(power.get("collector", 0) or 0) * scale))
    if collector_w > 0:
        labels.append("collector")
        weights.append(collector_w)
    return str(rng.choices(labels, weights=weights, k=1)[0])


def _is_adjacent_8(a_reel: int, a_row: int, b_reel: int, b_row: int) -> bool:
    return (b_reel - a_reel, b_row - a_row) in ADJACENT_8


def _build_coin_reveal(
    reel: int,
    row: int,
    symbol: str,
    tile_level: int,
    value: float,
    *,
    round_index: int = 1,
    power_resolved: bool = False,
) -> dict:
    # Hard face integers only — label == pay (no soft scale).
    display_value = int(round(float(value)))
    paid = float(display_value)
    item = {
        "reel": reel,
        "row": row,
        "kind": "coin",
        "symbol": symbol,
        "value": display_value,
        "displayValue": display_value,
        "tileLevel": tile_level,
        "tileMultiplier": 1,
        "resolvedValue": paid,
        "payout": paid,
        "round": round_index,
    }
    if power_resolved:
        item["powerResolved"] = True
    return item


def _build_multi_reveal(
    reel: int,
    row: int,
    multi: int,
    tile_level: int,
    *,
    round_index: int = 1,
) -> dict:
    face = int(multi)
    return {
        "reel": reel,
        "row": row,
        "kind": "multiplier",
        "symbol": "XM",
        "value": face,
        "displayValue": face,
        "tileLevel": max(int(tile_level), 1),
        "tileMultiplier": 1,
        "resolvedValue": face,
        # MULTI itself does not pay — adjacent coins carry the multiplied faces.
        "payout": 0,
        "round": round_index,
    }


def _build_collector_reveal(
    reel: int,
    row: int,
    tile_level: int,
    *,
    round_index: int = 1,
    reactivate: bool = False,
) -> dict:
    item = {
        "reel": reel,
        "row": row,
        "kind": "collector",
        "symbol": "CL",
        "value": 0,
        "displayValue": 0,
        "tileLevel": max(int(tile_level), 1),
        "tileMultiplier": 1,
        "resolvedValue": 0,
        "payout": 0,
        "round": round_index,
    }
    if reactivate:
        item["reactivate"] = True
    return item


def _item_pos(item: dict) -> tuple[int, int]:
    return (int(item["reel"]), int(item["row"]))


def _is_collected(item: dict) -> bool:
    return bool(item.get("collected"))


def _column_sort_key(item: dict) -> tuple[int, int]:
    return _item_pos(item)


def _active_collectors(items: list[dict], counted_cells: set[tuple[int, int]] | None = None) -> list[dict]:
    skip = counted_cells or set()
    return [
        item
        for item in items
        if item.get("kind") == "collector"
        and not _is_collected(item)
        and _item_pos(item) not in skip
    ]


def _leftmost_collector(
    items: list[dict], counted_cells: set[tuple[int, int]] | None = None
) -> dict | None:
    pots = _active_collectors(items, counted_cells)
    if not pots:
        return None
    pots.sort(key=_column_sort_key)
    return pots[0]


def _active_multis(items: list[dict]) -> list[dict]:
    return [
        item
        for item in items
        if item.get("kind") == "multiplier" and not item.get("powerResolved")
    ]


def _leftmost_multi(items: list[dict]) -> dict | None:
    heads = _active_multis(items)
    if not heads:
        return None
    heads.sort(key=_column_sort_key)
    return heads[0]


def _mark_acting_multi(items: list[dict], at_reel: int, at_row: int) -> list[dict]:
    out: list[dict] = []
    for item in items:
        cloned = dict(item)
        if cloned.get("kind") == "multiplier" and _item_pos(cloned) == (at_reel, at_row):
            cloned["powerResolved"] = True
        out.append(cloned)
    return out


def _is_spent_pot(item: dict) -> bool:
    """Valued pot that already vacuumed — waiting to be sucked, not a new actor."""
    return (
        item.get("kind") == "collector"
        and bool(item.get("powerResolved"))
        and not _is_collected(item)
    )


def _is_valued_pot(item: dict) -> bool:
    """A pot that already has a face — unused empty bags wait instead."""
    if item.get("kind") != "collector" or _is_collected(item):
        return False
    return bool(item.get("powerResolved")) or _collector_face(item) > 0


def _apply_collector(
    items: list[dict],
    at_reel: int,
    at_row: int,
    skip_pots: set[tuple[int, int]] | None = None,
) -> list[dict]:
    """Vacuum coins and valued pots. Unused empty bags wait for their own turn.

    `skip_pots` are already-credited last pots — leftover coins only, never suck them.
    """
    locked = skip_pots or set()
    absorbed = 0.0
    acting_face = 0.0
    for item in items:
        pos = _item_pos(item)
        if pos == (at_reel, at_row):
            acting_face = float(_collector_face(item))
            continue
        if pos in locked:
            continue
        if _is_collected(item):
            continue
        if item.get("kind") == "coin" or _is_valued_pot(item):
            absorbed += float(item.get("payout") or item.get("displayValue") or 0)
    leftover = 0
    for item in items:
        if item.get("kind") != "coin" or _is_collected(item):
            continue
        if _item_pos(item) in locked:
            leftover += int(round(float(item.get("payout") or item.get("displayValue") or 0)))
    face = _cap_pot_to_board(acting_face + absorbed, leftover)
    out: list[dict] = []
    for item in items:
        cloned = dict(item)
        pos = _item_pos(cloned)
        kind = cloned.get("kind")
        if kind == "collector" and pos == (at_reel, at_row):
            cloned["value"] = face
            cloned["displayValue"] = face
            cloned["resolvedValue"] = float(face)
            cloned["payout"] = float(face)
            cloned["powerResolved"] = True
            cloned.pop("collected", None)
        elif kind == "coin" and not _is_collected(cloned):
            cloned["collected"] = True
            cloned["powerResolved"] = True
            cloned["payout"] = 0.0
        elif (
            kind == "collector"
            and pos != (at_reel, at_row)
            and pos not in locked
            and _is_valued_pot(cloned)
        ):
            cloned["collected"] = True
            cloned["powerResolved"] = True
            cloned["payout"] = 0.0
        out.append(cloned)
    return out


def _stamp_round(items: list[dict], round_index: int, action: str | None = None) -> list[dict]:
    stamped: list[dict] = []
    for item in items:
        cloned = dict(item)
        cloned["round"] = round_index
        if action:
            cloned["action"] = action
        else:
            cloned.pop("action", None)
        stamped.append(cloned)
    return stamped


# Safety cap across clover + collector actions so a full-board chain can finish.
MAX_POWER_ACTIONS = 30
MAX_COLLECTOR_REGENS = MAX_POWER_ACTIONS
COIN_FEATURE_WINCAP = 25000


# Trifecta live board: clovers sit on corners so each one multiplies its own coins.
_PEAK_CLOVER_SPOTS = [(1, 0), (1, 4), (4, 0), (4, 4)]
_PEAK_POT_SPOT = (0, 2)


def _peak_show_roll(
    gamestate: "GameExecutables",
    rng: random.Random,
    positions: list[tuple[int, int]],
    round_index: int,
) -> tuple[list[dict], list[tuple[int, int, int]], list[tuple[int, int]]]:
    """Several 2x/3x clovers and one pot, on small gold faces.

    Reruns replace the spent cells with 25-coins, so the resolved total stays
    near the 1,926x live average instead of running away to the cap.
    """
    spot = set(positions)
    pot = _PEAK_POT_SPOT if _PEAK_POT_SPOT in spot else positions[0]
    clover_spots = [pos for pos in _PEAK_CLOVER_SPOTS if pos in spot and pos != pot]
    roll = rng.random()
    count = 4 if roll < 0.62 else 3 if roll < 0.92 else 2
    chosen = clover_spots[:count]
    items: list[dict] = [_build_collector_reveal(pot[0], pot[1], 3, round_index=round_index)]
    multis: list[tuple[int, int, int]] = []
    for index, (reel, row) in enumerate(chosen):
        # Mostly 2x, with a 3x often enough that the board reads as an event.
        multi = 3 if rng.random() < (0.42 if index == 0 else 0.28) else 2
        items.append(_build_multi_reveal(reel, row, multi, 3, round_index=round_index))
        multis.append((reel, row, multi))
    chosen_set = set(chosen)
    for reel, row in positions:
        if (reel, row) == pot or (reel, row) in chosen_set:
            continue
        value = 50 if rng.random() < 0.06 else 25
        items.append(_build_coin_reveal(reel, row, "CG", 3, value, round_index=round_index))
    return items, multis, [pot]


def _ensure_small_game_clover(
    gamestate: "GameExecutables", rng: random.Random, working: list[dict]
) -> list[dict]:
    """A small stack of coins shows a 2x or 3x even when the roll missed.

    The clover replaces the smallest coin that actually touches another coin,
    so the extra multiplier is a couple of small faces, not a gold chain.
    """
    if getattr(gamestate, "betmode", None) == "peak_spin":
        return working
    # Tests park every tier at 0 clovers when they want a coin-only resolve.
    table = getattr(gamestate.config, "coin_game_power_by_tile_level", {}) or {}
    if table and all(int((profile or {}).get("multiplier", 0) or 0) <= 0 for profile in table.values()):
        return working
    if any(item.get("kind") == "multiplier" for item in working):
        return working
    coins = [item for item in working if item.get("kind") == "coin"]
    if len(coins) < 2:
        return working
    opening = sum(int(item.get("value") or 0) for item in coins)
    if opening >= 60:
        return working

    def neighbors(item: dict) -> int:
        reel, row = _item_pos(item)
        return sum(
            1
            for other in coins
            if other is not item and _is_adjacent_8(reel, row, *_item_pos(other))
        )

    coins.sort(key=lambda item: (-neighbors(item), int(item.get("value") or 0), _item_pos(item)))
    victim = coins[0]
    multi = 2 if rng.random() < 0.68 else 3
    replacement = _build_multi_reveal(
        int(victim["reel"]),
        int(victim["row"]),
        multi,
        int(victim.get("tileLevel") or 1),
        round_index=int(victim.get("round") or 1),
    )
    victim_pos = _item_pos(victim)
    return [replacement if _item_pos(item) == victim_pos else item for item in working]


def _roll_prizes(
    gamestate: "GameExecutables",
    rng: random.Random,
    positions: list[tuple[int, int]],
    round_index: int,
    *,
    reactivate: bool = False,
) -> tuple[list[dict], list[tuple[int, int, int]], list[tuple[int, int]]]:
    if getattr(gamestate, "betmode", None) == "peak_spin" and not reactivate:
        return _peak_show_roll(gamestate, rng, positions, round_index)
    round_items: list[dict] = []
    multis: list[tuple[int, int, int]] = []
    collectors: list[tuple[int, int]] = []
    for reel, row in positions:
        tile_level = int(gamestate.tile_levels[reel][row])
        physical = _physical_coin_payout(gamestate, reel, row, tile_level)
        if physical is not None:
            symbol, value = physical
            item = _build_coin_reveal(reel, row, symbol, tile_level, value, round_index=round_index)
            if reactivate:
                item["reactivate"] = True
            round_items.append(item)
            continue
        kind = _pick_cell_kind(gamestate, rng, tile_level, reactivate=reactivate)
        if kind == "multiplier":
            multi = _pick_multi_value(gamestate, rng)
            item = _build_multi_reveal(reel, row, multi, tile_level, round_index=round_index)
            if reactivate:
                item["reactivate"] = True
            round_items.append(item)
            multis.append((reel, row, multi))
            continue
        if kind == "collector":
            item = _build_collector_reveal(
                reel, row, tile_level, round_index=round_index, reactivate=reactivate
            )
            round_items.append(item)
            collectors.append((reel, row))
            continue
        value = float(_pick_weighted_coin_value(gamestate, tile_level, rng))
        symbol = _virtual_coin_symbol(tile_level)
        item = _build_coin_reveal(reel, row, symbol, tile_level, value, round_index=round_index)
        if reactivate:
            item["reactivate"] = True
        round_items.append(item)
    return round_items, multis, collectors


def _collector_face(item: dict) -> int:
    return int(
        round(
            float(
                item.get("displayValue")
                or item.get("payout")
                or item.get("resolvedValue")
                or item.get("value")
                or 0
            )
        )
    )


def _leftover_coin_sum(items: list[dict]) -> int:
    """Uncollected coin faces still on the board (not pots)."""
    total = 0
    for item in items:
        if item.get("kind") != "coin" or _is_collected(item):
            continue
        total += int(
            round(
                float(
                    item.get("payout")
                    or item.get("displayValue")
                    or item.get("value")
                    or 0
                )
            )
        )
    return total


def _cap_pot_to_board(raw_pot: float, leftover: float) -> int:
    """Pot face so pot + leftover coins never exceed 25,000×.

    If leftover already covers the cap, pot is 0 (caller gathers coins, then count-up).
    """
    leftover_n = max(0, int(round(float(leftover))))
    raw_n = max(0, int(round(float(raw_pot))))
    if leftover_n >= COIN_FEATURE_WINCAP:
        return 0
    if raw_n + leftover_n > COIN_FEATURE_WINCAP:
        return COIN_FEATURE_WINCAP - leftover_n
    return raw_n


def _board_at_wincap(items: list[dict]) -> bool:
    leftover = _leftover_coin_sum(items)
    if leftover >= COIN_FEATURE_WINCAP:
        return True
    pot_max = 0
    for item in items:
        if item.get("kind") == "collector" and not _is_collected(item):
            pot_max = max(pot_max, _collector_face(item))
    return leftover + pot_max >= COIN_FEATURE_WINCAP


def _apply_multi(
    items: list[dict],
    at_reel: int,
    at_row: int,
    multi: int,
    *,
    kinds: tuple[str, ...] = ("coin", "collector"),
    pot_hits: set[tuple[tuple[int, int], tuple[int, int]]] | None = None,
) -> list[dict]:
    """Multiply 8-way adjacent coins and valued pots. Collected coins are skipped."""
    factor = int(multi)
    multi_pos = (int(at_reel), int(at_row))
    mid: list[dict] = []
    for item in items:
        cloned = dict(item)
        adjacent = _is_adjacent_8(at_reel, at_row, int(cloned["reel"]), int(cloned["row"]))
        kind = cloned.get("kind")
        if (
            adjacent
            and kind == "coin"
            and "coin" in kinds
            and not cloned.get("collected")
        ):
            face = min(
                COIN_FEATURE_WINCAP,
                int(round(float(cloned.get("displayValue", cloned.get("value", 0))))) * factor,
            )
            cloned["value"] = face
            cloned["displayValue"] = face
            cloned["resolvedValue"] = float(face)
            cloned["payout"] = float(face)
            symbol, level = _coin_metal_for_face(face, int(cloned.get("tileLevel") or 1))
            cloned["symbol"] = symbol
            cloned["tileLevel"] = level
            cloned["powerResolved"] = True
        mid.append(cloned)

    leftover = _leftover_coin_sum(mid)
    out: list[dict] = []
    for cloned in mid:
        adjacent = _is_adjacent_8(at_reel, at_row, int(cloned["reel"]), int(cloned["row"]))
        kind = cloned.get("kind")
        if adjacent and kind == "collector" and "collector" in kinds:
            pot_pos = (int(cloned["reel"]), int(cloned["row"]))
            if pot_hits is not None and (multi_pos, pot_pos) in pot_hits:
                out.append(cloned)
                continue
            base = _collector_face(cloned)
            if base > 0:
                face = _cap_pot_to_board(base * factor, leftover)
                cloned = dict(cloned)
                cloned["value"] = face
                cloned["displayValue"] = face
                cloned["resolvedValue"] = float(face)
                cloned["payout"] = float(face)
                cloned["powerResolved"] = True
                if pot_hits is not None:
                    pot_hits.add((multi_pos, pot_pos))
        out.append(cloned)
    return out


def _apply_all_multis(
    items: list[dict],
    multis: list[tuple[int, int, int]],
    *,
    kinds: tuple[str, ...] = ("coin", "collector"),
    pot_hits: set[tuple[tuple[int, int], tuple[int, int]]] | None = None,
) -> list[dict]:
    resolved = [dict(item) for item in items]
    for at_reel, at_row, multi in multis:
        resolved = _apply_multi(
            resolved, at_reel, at_row, multi, kinds=kinds, pot_hits=pot_hits
        )
    return resolved


def _board_payout(items: list[dict]) -> float:
    total = 0.0
    for item in items:
        if _is_collected(item):
            continue
        total += float(item.get("payout", 0) or 0)
    return total


def _merge_replacements(working: list[dict], replacements: list[dict]) -> list[dict]:
    skip = {_item_pos(item) for item in replacements}
    return [item for item in working if _item_pos(item) not in skip] + replacements


def _replace_slots(
    gamestate: "GameExecutables",
    rng: random.Random,
    working: list[dict],
    positions: list[tuple[int, int]],
    round_index: int,
    all_items: list[dict],
) -> tuple[list[dict], int]:
    sitting_pots = {
        _item_pos(item)
        for item in working
        if item.get("kind") == "collector" and not _is_collected(item)
    }
    unique = sorted(
        (pos for pos in set(positions) if pos not in sitting_pots),
        key=lambda pos: (pos[0], pos[1]),
    )
    if not unique:
        return working, round_index
    round_index += 1
    rolled, _, _ = _roll_prizes(
        gamestate, rng, unique, round_index, reactivate=True
    )
    working = _stamp_round(_merge_replacements(working, rolled), round_index, "regen")
    all_items.extend(working)
    working = [_keep_prize(item) for item in working]
    return working, round_index


def _keep_prize(item: dict) -> dict:
    cloned = dict(item)
    cloned.pop("reactivate", None)
    cloned.pop("action", None)
    return cloned


def remove_coins_from_board(gamestate: "GameExecutables") -> list[tuple[int, int]]:
    """Remove all coin symbols from the board; clear stored coin values. Keep tiles."""
    removed: list[tuple[int, int]] = []
    coin_symbols = set(gamestate.config.coin_symbols)
    board = getattr(gamestate, "board", None) or []
    for reel in range(gamestate.config.num_reels):
        if reel >= len(board):
            continue
        for row in range(gamestate.config.num_rows[reel]):
            if row >= len(board[reel]):
                continue
            sym = board[reel][row]
            name = getattr(sym, "name", None)
            if name in coin_symbols:
                sym.explode = True
                removed.append((reel, row))
    gamestate.board_coin_values = {}
    return removed


def _mode_coin_scale(gamestate: "GameExecutables") -> float:
    """Legacy RTP lever — kept at 1.0 so faces stay hard (label = pay)."""
    scales = getattr(gamestate.config, "coin_tile_scale_by_mode", {}) or {}
    freegame = getattr(gamestate.config, "freegame_type", "freegame")
    if getattr(gamestate, "gametype", None) == freegame:
        variant = getattr(gamestate, "bonus_variant", None)
        if variant in ("hear", "speak", "madness"):
            key = "speak" if variant == "madness" else variant
            return float(scales.get(f"bonus_{key}", scales.get(f"bonus_{variant}", 1.0)))
    mode = getattr(gamestate, "betmode", "base")
    return float(scales.get(mode, 1.0))


def _mode_coin_cap(gamestate: "GameExecutables") -> int | None:
    """Max lit tiles that pay coins this activation (None = all lit)."""
    caps = getattr(gamestate.config, "max_activation_coins_by_mode", {}) or {}
    freegame = getattr(gamestate.config, "freegame_type", "freegame")
    if getattr(gamestate, "gametype", None) == freegame:
        variant = getattr(gamestate, "bonus_variant", None)
        if variant in ("hear", "speak", "madness"):
            key = "speak" if variant == "madness" else variant
            return caps.get(f"bonus_{key}", caps.get(f"bonus_{variant}"))
    mode = getattr(gamestate, "betmode", "base")
    return caps.get(mode)


def _physical_coins_land(gamestate: "GameExecutables") -> bool:
    """Feature Spin and free spins land CB/CS/CG. Base and TRIFECTA stay virtual."""
    if getattr(gamestate, "betmode", None) == "feature_spin":
        return True
    freegame = getattr(gamestate.config, "freegame_type", "freegame")
    return getattr(gamestate, "gametype", None) == freegame


def _physical_coin_payout(
    gamestate: "GameExecutables", reel: int, row: int, tile_level: int
) -> tuple[str, float] | None:
    """Landed coin pays its face × the tile multiplier (2 / 5 / 10)."""
    if not _physical_coins_land(gamestate):
        return None
    board = getattr(gamestate, "board", None) or []
    if reel >= len(board) or row >= len(board[reel]):
        return None
    symbol = getattr(board[reel][row], "name", None)
    if symbol not in set(getattr(gamestate.config, "coin_symbols", ()) or ()):
        return None
    stored = (getattr(gamestate, "board_coin_values", None) or {}).get((reel, row))
    if stored is None:
        return None
    multiplier = max(1, int(gamestate.level_to_multiplier(tile_level) or 1))
    return str(symbol), float(stored) * multiplier


def _use_virtual_coins(gamestate: "GameExecutables") -> bool:
    """False when this spin can pay landed bronze/silver/gold coins."""
    return not _physical_coins_land(gamestate)


def _coin_game_rng(gamestate: "GameExecutables") -> random.Random:
    """Per-spin stream. `simulation_seed` used to stay 0, so every activation reused Random(0)."""
    seed_base = getattr(gamestate, "simulation_seed", None)
    if seed_base is None:
        seed_base = getattr(gamestate, "sim", 0) or 0
    activation = int(getattr(gamestate, "progress_activation_count", 0) or 0)
    # repeat_count changes the stream when a book is rejected (cap or Speak floor).
    repeat = int(getattr(gamestate, "repeat_count", 0) or 0)
    return random.Random(int(seed_base) * 1_000_003 + activation * 9973 + repeat * 104729 + 17)


def resolve_coin_game(gamestate: "GameExecutables") -> tuple[float, list[dict], int]:
    """Flip every lit tile. Clovers, then the leftmost pot, then reruns.

    Events use the frontend kinds: coin, multiplier (clover), collector (pot).
    A rerun past the cap flags the book so it is thrown out, never shipped.
    """
    gamestate.coin_game_cap_hit = False
    return _resolve_virtual_coins(gamestate, _coin_game_rng(gamestate))


def _resolve_virtual_coins(
    gamestate: "GameExecutables", rng: random.Random
) -> tuple[float, list[dict], int]:
    """Roll prizes; clovers one at a time, then the leftmost pot.

    Collected coins, used clovers, and spent pots flip again. The loop stops
    when a rerun shows no new clover and no new pot. Pot weight on a rerun
    follows the tile tier, so pots can come back. Ten reruns is the cap.
    """
    positions = highlighted_positions(gamestate)
    if not positions:
        gamestate.coin_game_stats = {"reruns": 0, "capHit": False, "clovers": 0, "pots": 0}
        return 0.0, [], 0

    cap = int(getattr(gamestate.config, "coin_game_max_reruns", 10) or 10)
    all_items: list[dict] = []
    counted_pots = 0.0
    counted_cells: set[tuple[int, int]] = set()
    spent_cells: set[tuple[int, int]] = set()
    round_index = 1
    pot_hit_by: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    pending_count: tuple[int, int] | None = None
    need_cycle_regen = False
    reruns = 0

    working, _new_multis, _collectors = _roll_prizes(
        gamestate, rng, positions, round_index, reactivate=False
    )
    if not working:
        return 0.0, [], 0
    working = _ensure_small_game_clover(gamestate, rng, working)
    working = _stamp_round(working, round_index, "spawn")
    all_items.extend(working)

    def _stats(cap_hit: bool) -> dict:
        return {
            "reruns": reruns,
            "capHit": cap_hit,
            "clovers": sum(1 for item in all_items if item.get("kind") == "multiplier" and item.get("action") == "spawn"),
            "pots": sum(1 for item in all_items if item.get("kind") == "collector" and item.get("action") == "spawn"),
        }

    def _rerun(working_now, round_now, replace_now):
        nonlocal reruns
        if not replace_now:
            return working_now, round_now, False
        reruns += 1
        if reruns > cap:
            gamestate.coin_game_cap_hit = True
            gamestate.coin_game_stats = _stats(True)
            return working_now, round_now, True
        updated, round_out = _replace_slots(
            gamestate, rng, working_now, replace_now, round_now, all_items
        )
        return updated, round_out, False

    def _sitting_at_wincap() -> bool:
        leftover = _leftover_coin_sum(working)
        pot_max = 0
        for item in working:
            if item.get("kind") == "collector" and not _is_collected(item):
                pot_max = max(pot_max, _collector_face(item))
        if leftover + pot_max >= COIN_FEATURE_WINCAP and pot_max > 0:
            return True
        if leftover >= COIN_FEATURE_WINCAP:
            return _leftmost_collector(working, spent_cells) is None
        return False

    actions = 0
    while actions < MAX_POWER_ACTIONS:
        if gamestate.coin_game_cap_hit:
            break
        if _sitting_at_wincap():
            break
        acting_multi = _leftmost_multi(working)
        if acting_multi is not None:
            at_reel, at_row = _item_pos(acting_multi)
            multi = int(acting_multi.get("value") or 1)
            round_index += 1
            applied = _apply_multi(
                working,
                at_reel,
                at_row,
                multi,
                kinds=("coin", "collector"),
                pot_hits=pot_hit_by,
            )
            applied = _mark_acting_multi(applied, at_reel, at_row)
            working = _stamp_round(applied, round_index, "multi")
            all_items.extend(working)
            actions += 1
            continue

        if pending_count is not None:
            at_reel, at_row = pending_count
            acting_now = next(
                (
                    item
                    for item in working
                    if item.get("kind") == "collector"
                    and _item_pos(item) == pending_count
                    and not _is_collected(item)
                ),
                None,
            )
            if acting_now is not None:
                counted_pots += float(acting_now.get("payout") or 0)
                counted_cells.add((at_reel, at_row))
            pending_count = None
            actions += 1
            continue

        if need_cycle_regen:
            replace_now = [
                _item_pos(item)
                for item in working
                if _is_collected(item) or item.get("kind") == "multiplier"
            ]
            working, round_index, capped = _rerun(working, round_index, replace_now)
            if capped:
                break
            need_cycle_regen = False
            actions += 1
            continue

        acting = _leftmost_collector(working, spent_cells)
        if acting is None:
            break
        at_reel, at_row = _item_pos(acting)
        acting_pos = (at_reel, at_row)
        round_index += 1
        working = _stamp_round(
            _apply_collector(working, at_reel, at_row, counted_cells),
            round_index,
            "collect",
        )
        all_items.extend(working)
        spent_cells.add(acting_pos)
        acting_now = next((item for item in working if _item_pos(item) == acting_pos), None)
        if acting_now is not None and _board_at_wincap(working):
            pending_count = acting_pos
            actions += 1
            continue
        other_collector = any(
            item.get("kind") == "collector"
            and not _is_collected(item)
            and _item_pos(item) != acting_pos
            and _item_pos(item) not in spent_cells
            for item in working
        )
        if other_collector:
            need_cycle_regen = True
            pending_count = None
        else:
            pending_count = acting_pos
            replace_now = [
                _item_pos(item)
                for item in working
                if (_is_collected(item) or item.get("kind") == "multiplier")
                and _item_pos(item) != acting_pos
            ]
            working, round_index, capped = _rerun(working, round_index, replace_now)
            if capped:
                break
        actions += 1

    if gamestate.coin_game_cap_hit:
        return float(gamestate.config.wincap), all_items, reruns

    leftover = 0.0
    for item in working:
        if _is_collected(item):
            continue
        kind = item.get("kind")
        pos = _item_pos(item)
        if kind == "coin":
            leftover += float(item.get("payout") or 0)
        elif kind == "collector" and pos not in counted_cells:
            leftover += float(item.get("payout") or 0)
    total = min(float(COIN_FEATURE_WINCAP), counted_pots + leftover)
    total = min(total, float(gamestate.config.wincap))
    max_round = max((int(item.get("round") or 1) for item in all_items), default=1)
    gamestate.coin_game_stats = _stats(False)
    return round(total, 4), all_items, max_round


resolve_board_activation = resolve_coin_game
