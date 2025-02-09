from warnings import warn
from src.calculations.statistics import normalize
from src.config.constants import *
from typing import List, Dict


class BetMode:
    """
    ##Sample BetMode Input Criteria##
    name="base",
    title="Base Game",
    description="Starting Game Mode",
    rtp=0.97,
    cost=1.0,
    auto_close_disables=False,
    is_feature = False,
    is_enhanced_mode=False,
    is_buybonus=False,
    max_win=self.wincap,
    """

    def __init__(
        self,
        name: str,
        cost: float,
        rtp: float,
        max_win: float,
        auto_close_disables: bool,
        is_feature: bool,
        is_buybonus: bool,
        distributions: object,
    ):
        self._name = name
        self._cost = cost
        self._wincap = max_win
        self._auto_close_disabled = auto_close_disables
        self._is_feature = is_feature
        self._is_buybonus = is_buybonus
        self._distributions = distributions
        self.set_rtp(rtp)
        self.set_force_keys()

    def __repr__(self):
        return (
            f"BetMode(name={self._name},"
            f"cost={self._cost}, max_win={self._wincap}, rtp={self._rtp}, auto_close_disables={self._auto_close_disabled} "
            f"is_feature={self._is_feature}, is_buybonus={self._is_buybonus} "
        )

    def set_rtp(self, rtp: float) -> None:
        """Set mode RTP."""
        if rtp >= 1.0:
            raise Warning(f"Return To Player is >=1.0!: {rtp}")
        self._rtp = rtp

    def set_force_keys(self):
        """Initialize force keys."""
        self._force_keys = []

    def add_force_key(self, forceKey: list):
        """Update force keys."""
        self._force_keys.append(str(forceKey))  # type:ignore

    def lock_force_keys(self):
        """Fialise force keys."""
        self._force_keys = tuple(sorted(self._force_keys))

    def get_force_keys(self):
        """Return current force keys."""
        return self._force_keys

    def get_name(self):
        """Return mode name."""
        return self._name

    def get_cost(self):
        """Return mode cost."""
        return self._cost

    def get_feature(self):
        """Return feature."""
        return self._is_feature

    def get_auto_close_disabled(self):
        return self._auto_close_disabled

    def getBuyBonus(self):
        return self._is_buybonus

    def get_wincap(self):
        return self._wincap

    def get_rtp(self):
        return self._rtp

    def get_distributions(self):
        return self._distributions

    def get_distribution_conditions(self, targetCriteria: str) -> dict:
        for d in self.get_distributions():
            if d._criteria == targetCriteria:
                return d._conditions
        return RuntimeError(
            f"target critera: {targetCriteria} not found in betmode-distributions."
        )
