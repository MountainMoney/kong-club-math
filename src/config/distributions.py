from typing import Dict, Union
import json


class Distribution:
    def __init__(
        self,
        criteria: str = None,
        quota: int = 0,
        win_criteria: Union[float, None] = None,
        conditions: dict = {},
        required_distribtion_conditions: list = [
            "reel_weights",
            "force_wincap",
            "force_freespins",
        ],
    ):

        assert quota > 0, "non-zero quota value must be assigned"

        self._quota = quota
        self._criteria = criteria
        self._required_distribtion_conditions = required_distribtion_conditions
        self._win_criteria = win_criteria
        self.verify_and_set_conditions(conditions)

    def dict_format(self) -> dict:
        dict_format = {
            "criteria": self._criteria,
            "rtp": self._rtp,
            "hr": self._hr,
            "avg": self._avg,
        }
        return dict_format

    def verify_and_set_conditions(self, conditions):
        conditionKeys = list(conditions.keys())
        for rk in self._required_distribtion_conditions:
            assert (
                rk in conditionKeys
            ), f"condition missing required key: {rk}\n conditionKeys"
        self._conditions = conditions

    def get_criteria(self):
        return self._criteria

    def get_quota(self):
        return self._quota

    def get_win_criteria(self):
        return self._win_criteria

    def get_required_distribution_conditions(self):
        return self._required_distribtion_conditions

    def __str__(self):
        return f"Criteria: {self._criteria}\nConditions: {json.dumps(self._conditions)}"

    def __repr__(self):
        return f"Criteria: {self._criteria}\nAvg. Win: {self._avg}\n RTP: {self._rtp}\n Hit-Rate: {self._hr}"


class DistributionConditions:
    def __init__(
        self, criteria: str, **kwargs: Dict[str, Dict[str, Union[float, int]]]
    ):
        """
        DistributionCondition keys must match Distribution
        """
        conditions = {}
        for dis, cond in kwargs:
            conditions[dis] = {"distribution": criteria, "conditions": cond}
        return conditions
