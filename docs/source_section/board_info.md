## Game Board

The `Board` class inherits the [`GeneraGameState`](state_info.md) class and handles the generation of game boards. Most commonly used is the `create_board_reelstrips()` function. Which selects a reelset as defined in the `BetMode.Distribution.conditions` class. For each reel a random stopping position is chosen with uniform probability on the range *[0,len(reelstrip[reel])-1]*. For each reelstop a 2D list of `Symbol` objects are created and attached to the GameState object. 

Additionally, special symbol information is included (*special_symbols_on_board*) along with the reelstop values (*reel_positions*), padding symbols directly above and below the active board (*padding_positions*) and which reelstip-id was used.

The is also an *anticipation* field which is used for adding a delay to reel reveals if the number of Scatters required for trigging the freegame is almost satisfied. This is an array of values initialized to `0` and counting upwards in `+1` value increments. For example if 3 Scatter symbols are needed to trigger the freegame and there are Scatters revealed on reels 0 and 1, the array would take the form (for a 5 reel game):
```python
self.anticipation = [0, 0, 1, 2, 3]
```

If the selected reel_pos + the length of the board is greater than the total reelstrip length, the stopping position is wrapped around to the 0 index:
```python
 self.reelstrip[reel][(reel_pos - 1) % len(self.reelstrip[reel])]
```

The reelset used is drawn from the weighted possible reelstrips as defined in the `BetMode.betmode.distributions.conditions` class (and hence is a required field in the `BetMode` object):
```python
    self.reelstrip_id = get_random_outcome(
        self.get_current_distribution_conditions()["reel_weights"][self.gametype]
    )
```