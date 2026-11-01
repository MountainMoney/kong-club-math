"""Compatibility entrypoint for scratch progress/activation tests."""

from test_scratch_rebuild import (
    test_tiles_coins_progress_activation_and_feature_prefill,
)


if __name__ == "__main__":
    test_tiles_coins_progress_activation_and_feature_prefill()
    print("test_progress_bar: all passed")
