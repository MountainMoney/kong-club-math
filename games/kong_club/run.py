"""Generate Kong Club math artifacts."""

from pathlib import Path
import os
import sys

SDK_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SDK_ROOT))

from gamestate import GameState
from game_config import GameConfig
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs


def sync_publish_luts(gamestate, modes):
    """Copy lookup_tables CSVs into publish_files _0.csv (SDK skips if _0 already exists)."""
    import shutil

    for mode in modes:
        src = gamestate.output_files.get_final_lookup_name(mode)
        dst = gamestate.output_files.get_optimized_lookup_name(mode)
        if os.path.exists(src):
            shutil.copy2(src, dst)


if __name__ == "__main__":
    import os

    smoke = os.environ.get("MM_SMOKE", "").lower() in ("1", "true", "yes")
    sims_per_mode = int(os.environ.get("MM_SIMS", "500"))
    if smoke:
        sims_per_mode = min(sims_per_mode, 1_000)
    base_sims = int(os.environ.get("MM_BASE_SIMS", str(sims_per_mode)))
    if smoke:
        base_sims = min(base_sims, 1_000)
    num_threads = 4 if sims_per_mode <= 10_000 else 10
    rust_threads = 4
    batching_size = min(2_500, max(250, sims_per_mode // 4))
    compression = True
    profiling = False
    num_sim_args = {
        "base": int(base_sims),
        "base_ante": int(base_sims),
        "hunt_2": int(sims_per_mode),
        "hunt_3": int(sims_per_mode),
        "hunt_4": int(sims_per_mode),
        "hunt_5": int(sims_per_mode),
        "feature_spin": int(sims_per_mode),
        "peak_spin": int(sims_per_mode),
        "bonus_see": int(sims_per_mode),
        "bonus_hear": int(sims_per_mode),
        "bonus_pick": int(sims_per_mode),
        "bonus_risky": int(sims_per_mode),
    }
    modes_filter = os.environ.get("MM_MODES", "").strip()
    if modes_filter:
        allowed = {m.strip() for m in modes_filter.split(",") if m.strip()}
        num_sim_args = {k: v for k, v in num_sim_args.items() if k in allowed}

    run_conditions = {
        "run_sims": True,
        "run_analysis": False,
        "run_format_checks": False,
    }

    print(f"Kong Club sims: base/ante {base_sims}, other modes {sims_per_mode} (batch={batching_size}, threads={num_threads})")

    config = GameConfig()
    gamestate = GameState(config)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )
        sync_publish_luts(gamestate, [m for m in num_sim_args if num_sim_args[m] > 0])

    generate_configs(gamestate)

