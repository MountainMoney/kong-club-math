"""Compatibility entrypoint for scratch tile tests."""

from test_scratch_rebuild import (
    test_tiles_coins_progress_activation_and_feature_prefill,
    test_wild_substitution_and_wild_removal,
)


if __name__ == "__main__":
    test_wild_substitution_and_wild_removal()
    test_tiles_coins_progress_activation_and_feature_prefill()
    print("test_level_up_tiles: all passed")
