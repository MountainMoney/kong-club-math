"""
Verify lookup-tale and book result format
Output statistics tested via RGS
"""

import json
import os
import importlib
from io import TextIOWrapper
import numpy as np
import zstandard as zst


def verify_lookup_format(filename: str) -> list:
    "Duplicate RGS verification before upload."
    integer_payouts = []
    running_weight_total = 0
    with open(filename, "r", encoding="UTF-8") as f:
        for line in f:
            _, weight, payout = line.strip().split(",")
            weight = float(weight)
            payout = float(payout)

            # Payout checks
            assert payout.is_integer() and payout >= 0, "Payout mult be uint64 format:"
            if payout > 0:
                assert payout >= 10, "Minimum non-zero payout is 10 (RGS accepts 'cents' increments)."
            assert payout % 10 == 0, "Payout values must be in increments of 10."
            integer_payouts.append(int(payout))

            # Weight checks
            assert weight.is_integer() and weight >= 0, "Weight must be uint64 format."
            # running_weight_total += np.uint128(weight)

    # assert running_weight_total <= np.uint64.max, "Sum of weights must be <= MAX(uint64)"

    return integer_payouts


# payout mult value match to lut + length match
def verify_books_and_payout_mults(books_filename: str) -> list:
    """Ensure the values written to the books match those in the lookup table exactly."""
    assert str(books_filename).endswith(".jsonl.zstd") or str(books_filename).endswith(
        "jsonl.zst"
    ), "Verification is only run for compressed book files of format .jsonl.zst."

    book_payout_ints = []
    with open(books_filename, "rb") as f:
        decompressor = zst.ZstdDecompressor()
        with decompressor.stream_reader(f) as reader:
            txt_stream = TextIOWrapper(reader, encoding="UTF-8")
            for line in txt_stream:
                line = line.strip()
                if not line:
                    continue

                try:
                    blob = json.loads(line)
                except json.JSONDecodeError:
                    raise RuntimeError("Invalid JSON format.")

                for key in ["payoutMultiplier", "id", "events"]:
                    if key not in blob:
                        raise RuntimeError(f"Missing required key: {key}")

                book_payout_ints.append(blob["payoutMultiplier"])

    return book_payout_ints


def compare_payout_values(book_int_payouts, lut_int_payouts) -> None:
    """Ensure payout multiplier values match between books and lookup tables."""
    assert len(book_int_payouts) == len(lut_int_payouts), "Mismatch in payout array size."
    for idx, _ in enumerate(book_int_payouts):
        assert book_int_payouts[idx] == lut_int_payouts[idx], "Payout mismatch between lookup table and book."


def get_lut_statistics(lut_filename):
    """Run RGS statistic tests for upload verification."""
    raise NotImplementedError("put this in")


def execute_all_tests(config, excluded_modes=[]):
    """Run all tests for a given game"""
    for bet_mode in config.bet_modes:
        name = bet_mode.get_name()
        if name not in excluded_modes:
            book_name = f"books_{name}.jsonl.zst"
            lookup_name = f"lookUpTable_{name}_0.csv"
            book_file = os.path.join(config.publish_path, book_name)
            lut_file = os.path.join(config.publish_path, lookup_name)

            if not (os.path.exists(book_file)) or not (os.path.exists(lut_file)):
                raise RuntimeError("Books/Lookup file does not exist.")

            lut_payouts = verify_lookup_format(lut_file)
            book_payouts = verify_books_and_payout_mults(book_file)

            compare_payout_values(book_payouts, lut_payouts)

            get_lut_statistics(lut_file)


def load_game_config(game_id: str):
    """Load game config class"""
    module_path = f"games.{game_id}.game_config"
    module = importlib.import_module(module_path)
    config = getattr(module, "GameConfig")

    return config()


if __name__ == "__main__":

    game_id = "0_0_lines"
    GameConfig = load_game_config(game_id)
    execute_all_tests(GameConfig)
