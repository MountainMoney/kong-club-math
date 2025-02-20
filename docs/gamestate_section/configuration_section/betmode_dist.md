# Distribution Conditions

Within each `BetMode` there is a set of `Distribution` Classes which determine the win-criteria within each bet-mode. Required fields are:

1. Criteria
    * A shorthand name describing the win condition in a single word
2. Quota
    * This is the amount of simulations (as a ratio of the total number of bet-mode simulation) which need to satisfy the corresponding criteria. The quota is normalised when assigning criteria to simulations, so the sum of all quotas does not need to be 1. There is a minimum of 1 simulation assigned per criteria.
3. Conditions
    * Conditions can have an arbitary number of keys. Though the required keys are:
        * `reel_weights` 
        * `force_wincap`
        * `force_freespins`

    The most common use for the Distribution Conditions is when drawing a random value using the BetMode's built-in method `get_distribution_conditions()`. i.e.
    ```python
        multiplplier = get_random_outcome(betmode.get_distribution_conditions()['mult_values'])
    ```
    Or to check if a board forcing the `freegame` should be drawn with:
    ```python
    if get_distribution_conditions()['force_freespins']:
        ...
    ```

    Optionally there is also a `win_criteria` condition which incorporates a payout multiplier into the simulation acceptance. The two commonly used condtions are `win_criteria = 0.0` and `win_criteria = self.wincap`. When calling `self.check_repeat()` at the end of a simulation, if `win_criteria` is not `None` (default), the final win amount must match the value passed. 

    The intention behind betmode distribution conditions is to give the option to handle game actions in a way which depends on the (known) expected simulation. This is most clear if for example a simulation is known to correspond to a `max-win` scenario. Instead of repeatly drawing random outcomes which are most likely to be rejected, we can alter the probabilties of larger payouts occurring by biasing a particular reelset, weighting larger prize or multiplier values etc..