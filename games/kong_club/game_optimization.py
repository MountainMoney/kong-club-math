"""Set Kong Club optimization parameters."""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructFenceBias,
    ConstructConditions,
    verify_optimization_input,
)


class OptimizationSetup:
    """Optimization scaffolding for all Kong Club modes."""

    def __init__(self, game_config):
        self.game_config = game_config
        wincaps = {bm.get_name(): bm.get_wincap() for bm in game_config.bet_modes}

        def params(test_spins):
            return ConstructParameters(
                num_show=5000,
                num_per_fence=10000,
                min_m2m=4,
                max_m2m=12,
                pmb_rtp=1.0,
                sim_trials=5000,
                test_spins=test_spins,
                test_weights=[1 / len(test_spins)] * len(test_spins),
                score_type="rtp",
            ).return_dict()

        self.game_config.opt_params = {
            "base": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.0, av_win=wincaps["base"], hr="x", search_conditions=wincaps["base"]
                    ).return_dict(),
                    "freegame": ConstructConditions(rtp=0.15, hr=400, search_conditions={"symbol": "scatter"}).return_dict(),
                    "board_activation": ConstructConditions(
                        rtp=0.52, hr=7, search_conditions={"symbol": "BOARD"}
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, hr="x", search_conditions=0).return_dict(),
                    "cap": ConstructConditions(
                        rtp=0.10, av_win=wincaps["base"], hr="x", search_conditions=wincaps["base"]
                    ).return_dict(),
                    "basegame": ConstructConditions(hr=4.5, rtp=0.1801).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 1.0, "win_range": (1, 3), "probability": 1.0},
                        {"criteria": "board_activation", "scale_factor": 1.0, "win_range": (50, 500), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.0, "win_range": (200, 1000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": params([100, 500, 1000]),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["basegame"], bias_ranges=[(0.5, 1.5)], bias_weights=[0.5]
                ).return_dict(),
            },
            "base_ante": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.01, av_win=wincaps["base_ante"], hr="x", search_conditions=wincaps["base_ante"]
                    ).return_dict(),
                    "ante_scatter": ConstructConditions(
                        rtp=0.24, hr=200, search_conditions={"symbol": "scatter"}
                    ).return_dict(),
                    "board_activation": ConstructConditions(
                        rtp=0.45, hr=6, search_conditions={"symbol": "BOARD"}
                    ).return_dict(),
                    "basegame": ConstructConditions(hr=4.0, rtp=0.2601).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 1.0, "win_range": (1, 5), "probability": 1.0},
                        {"criteria": "ante_scatter", "scale_factor": 1.1, "win_range": (100, 1000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": params([100, 500, 1000]),
            },
            "bonus_see": {
                "conditions": {
                    "bonus_low": ConstructConditions(rtp=0.30, av_win=30, hr="x", search_conditions=(0, 50)).return_dict(),
                    "bonus_high": ConstructConditions(rtp=0.35, av_win=150, hr="x", search_conditions=(50, 1000)).return_dict(),
                    "freegame": ConstructConditions(rtp=0.3001, hr="x").return_dict(),
                    "wincap": ConstructConditions(
                        rtp=0.01, av_win=wincaps["bonus_see"], hr="x", search_conditions=wincaps["bonus_see"]
                    ).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "bonus_low", "scale_factor": 1.0, "win_range": (5, 50), "probability": 1.0},
                        {"criteria": "bonus_high", "scale_factor": 1.0, "win_range": (50, 1000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": params([10, 50, 100]),
            },
            "bonus_hear": {
                "conditions": {
                    "bonus_low": ConstructConditions(rtp=0.25, av_win=40, hr="x", search_conditions=(0, 75)).return_dict(),
                    "bonus_high": ConstructConditions(rtp=0.45, av_win=250, hr="x", search_conditions=(75, 1500)).return_dict(),
                    "freegame": ConstructConditions(rtp=0.2501, hr="x").return_dict(),
                    "wincap": ConstructConditions(
                        rtp=0.01, av_win=wincaps["bonus_hear"], hr="x", search_conditions=wincaps["bonus_hear"]
                    ).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "bonus_low", "scale_factor": 1.0, "win_range": (5, 75), "probability": 1.0},
                        {"criteria": "bonus_high", "scale_factor": 1.1, "win_range": (75, 1500), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": params([10, 50, 100]),
            },
            "feature_spin": {
                "conditions": {
                    "nibble": ConstructConditions(rtp=0.1200, hr="x").return_dict(),
                    "run": ConstructConditions(rtp=0.8401, hr="x").return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "nibble", "scale_factor": 1.0, "win_range": (1, 25), "probability": 1.0},
                        {"criteria": "run", "scale_factor": 1.0, "win_range": (25, 400), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": params([50, 100, 200]),
            },
            "peak_spin": {
                "conditions": {
                    "dead_juicy": ConstructConditions(rtp=0.0, av_win=0, hr="x", search_conditions=0).return_dict(),
                    "nibble": ConstructConditions(rtp=0.0400, hr="x").return_dict(),
                    "run": ConstructConditions(rtp=0.1200, hr="x").return_dict(),
                    "clip": ConstructConditions(rtp=0.4000, hr="x").return_dict(),
                    "tease": ConstructConditions(rtp=0.3951, hr="x").return_dict(),
                    "cap": ConstructConditions(
                        rtp=0.0050, av_win=wincaps["peak_spin"], hr="x", search_conditions=wincaps["peak_spin"]
                    ).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "nibble", "scale_factor": 1.0, "win_range": (1, 2000), "probability": 1.0},
                        {"criteria": "clip", "scale_factor": 1.0, "win_range": (8000, 16000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": params([10, 50, 100]),
            },
            "bonus_gamble": {
                "conditions": {
                    "gamble_dead": ConstructConditions(rtp=0.0, av_win=0, hr="x", search_conditions=0).return_dict(),
                    "gamble_hear": ConstructConditions(rtp=0.6401, hr="x").return_dict(),
                    "gamble_madness": ConstructConditions(rtp=0.3200, hr="x").return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "gamble_hear", "scale_factor": 1.0, "win_range": (20, 400), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": params([10, 50, 100]),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
