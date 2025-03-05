"""Construct optimization class from GameConfig.bet_mode specifications."""


class BetmodeOptimization:
    def __init__(self, betmode_name: str, conditions: dict, scaling: list):
        self.betmode_name = betmode_name
        self.conditions = conditions
        self.scaling = scaling


class OptimizationParameters:
    """Construct optimization parameter class for each bet mode."""

    # TODO: PUT IN OPPOSITE AND DEFAULT "X" CONDITIONS

    def __init__(
        self,
        rtp: float = None,
        av_win: float = None,
        hr: float = None,
        search_conditions=None,
    ):
        # assert type(search_conditions) in [
        #     float,
        #     int,
        #     tuple,
        #     dict,
        #     None,
        # ], "Must specify strict payout, range, or force-file search dictionary."

        none_count = sum([1 for x in [rtp, av_win, hr] if x is None])
        assert none_count == 1, "1 of 3 values (rtp, av_win, hr) must be 'None'"

        if rtp is None:
            rtp = round(av_win / hr, 5)
        elif av_win is None:
            av_win = round(rtp * hr, 5)
        elif hr is None:
            if rtp != 0:
                hr = round(av_win / rtp, 5)
            else:
                hr = None

        search_range, force_search = (-1, -1), {}
        if isinstance(search_conditions, (float, int)):
            search_range = (search_conditions, search_conditions)
            force_search = {}
        elif isinstance(search_conditions, tuple):
            assert search_conditions[0] <= search_conditions[1], "Enter (min, max) payout format."
            search_range = search_conditions
            force_search = {}
        elif isinstance(search_conditions, dict):
            search_range = (-1, -1)
            force_search = search_conditions

        self.rtp = rtp
        self.av_win = av_win
        self.hr = hr
        self.search_range = search_range
        self.force_search = force_search
        self.params = self.to_dict()

    def to_dict(self):
        """JSON readable"""
        data_struct = {
            "rtp": self.rtp,
            "hr": self.hr,
            "av_win": self.av_win,
            "search_range": self.search_range,
            "force_search": self.force_search,
        }
        return data_struct
