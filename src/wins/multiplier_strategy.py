"""Global multipliers, symbol multipliers, combined multipliers or no actions
    All functions return [final_win_amount], [applied multiplier]"""

from typing import List, Dict
from src.calculations.board import Board


def apply_mult(
    board: Board,
    strategy: str,
    win_amount: float = 0.0,
    global_multiplier: int = 1,
    positions: list = [],
):
    """Apply multiplier method to win_amount and winning symbol positions."""
    strat = {
        "global": apply_global_mult(win_amount, global_multiplier),
        "symbol": apply_added_symbol_mult(board, win_amount, positions),
        "combined": apply_combined_mult(board, win_amount, global_multiplier, positions),
    }
    return strat[strategy]


def apply_global_mult(win_amount: float, global_multiplier: int) -> tuple:
    """Enhance win global multiplier"""
    return (round(win_amount * global_multiplier, 2), global_multiplier)


def apply_added_symbol_mult(board: Board, win_amount: float, positions: List[Dict]) -> tuple:
    """Get multiplier attribute from all winning positions"""
    symbol_multiplier = 0
    for pos in positions:
        if (
            board[pos["reel"]][pos["row"]].check_attribute("multiplier")
            and board[pos["reel"]][pos["row"]].get_attribute("multiplier") > 1
        ):
            symbol_multiplier += board[pos["reel"]][pos["row"]].get_attribute("multiplier")
    return (round(win_amount * max(symbol_multiplier, 1), 2), max(symbol_multiplier, 1))


def apply_combined_mult(board: Board, win_amount: float, global_multiplier: int, positions: List[Dict]) -> tuple:
    """Apply symbol multipliers and then global multiplier"""
    win, sym_mult = apply_added_symbol_mult(board, win_amount, positions)
    return (win, sym_mult * global_multiplier)
