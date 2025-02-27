# The State Machine

## Introduction
When initializing a simulation batch, the **GameState** class serves as a central hub that manages all simulation aspects, including:

- Simulation parameters
- All game modes
- Configuration settings
- Simulation results
- Output files

This class acts as a super-class, ensuring shared components across all simulations. The entry point for all game simulations is the `run.py` file, which sets up parameters through the [Config](../source_section/config_info.md) class and initializes a [GameState](../source_section/state_info.md) object. The **GameState** handles crucial aspects such as:

#### Simulation Configuration
- Compression
- Tracing
- Multithreading
- Output files
- Cumulative win manager

#### Game Configuration
- Betmode details (costs, name, etc..)
- Paytable
- Symbols
- Reelsets


These **global `GameState` attributes** remain consistent across all game modes, and simulations. When a simulation runs, `run_spin()` creates a sub-instance of the **General GameState**, allowing modifications to game data through the `self` object. The central idea is that the **GameState** represents the current state of the simulation. And components within this state are modified directly. This reduces the need to be passing objects back and forth between functions when writing game logic. 


At a high-level, the structure of the engine is shown: 
![below](../engine_flowchart.png)


There is a super-class containing essentially all core functionality. When setting up a custom game, these events will extend (or override) the core functionality as per Python's Method Resolution Order (MRO). This `GameState` class is then used to keep track of simulation details. Once complete, all relevant output files are generated sequentially for each BetMode. Finally these outputs can be used for optimization before being uploaded/published to the Admin Control Panel (ACP).

## Class Inheritance

### Why Use Class Inheritance?
Class inheritance ensures flexibility, allowing developers to access core functions while customizing specific behaviors for each game. Core functions are found in the [Source Files](../source_section/win_manager.md) section and can be overridden at the game level.

#### **GameStateOverride (game/game_override.py)**
This class is the first in the **Method Resolution Order (MRO)** and is responsible for modifying or extending actions from the `state.py` file. All sample games override the `reset_book()` function to accommodate game-specific parameters.

Example:
```python
def reset_book(self):
    super().reset_book()
    self.reset_grid_mults()
    self.reset_grid_bool()
    self.tumble_win = 0
```

Each game has unique rules, such as cluster multipliers or cascading wins, which are set here.

#### **GameExecutables (game/game_executables.py)**
Executable functions group multiple game actions together. These functions can be overridden to introduce new mechanics at the game level.

In the case of triggering freespins, for example. Generally the number of scatters active on a game-board would be counted and the appropriate number of spins are assigned from the config file definition:
```python
config.freespin_triggers = {3:8 ,4:10, 5:12}
```
Where 3 scatters award 8 spins etc... This is a commonly carried out procedure, so there is a function in `Executables.update_freespin_amount()` to assign freespins,
```python
    def update_freespin_amount(self, scatter_key: str = "scatter") -> None:
        self.tot_fs = self.config.freespin_triggers[self.gametype][self.count_special_symbols(scatter_key)]
        fs_trigger_event(self, basegame_trigger=True, freegame_trigger=False)
```

However in the `0_0_scatter` sample game, we would instead want to assign the total spins to be 2x the number of active Scatters. Therefore we can override the function in the `GameExecutables` class:

```python
def update_freespin_amount(self, scatter_key: str = "scatter"):
    self.tot_fs = self.count_special_symbols(scatter_key) * 2
    fs_trigger_event(self, basegame_trigger=basegame_trigger, freegame_trigger=freegame_trigger)
```

#### **GameCalculations (games/game_calculations.py)**
This class handles game-specific calculations, inheriting from **GameExecutables**.

## Books and Libraries
### **What is a "Book"?**
A "book" represents a single simulation result, storing:
- The payout multiplier
- Events triggered during the round
- Win conditions

Each simulation generates a **Book** object, which is stored in a **library** and subsequently attached to the global **GameState** object. The contents of *book.events* is the data returned from the RGS *play/* API.

Example JSON structure:
```json
[
    {
        "id": int,
        "payoutMultiplier": float,
        "events": [ {}, {}, {} ],
        "criteria": str,
        "baseGameWins": float,
        "freeGameWins": float
    }
]
```

At the start of a simulation, the book is reset:
```python
def reset_book(self) -> None:
    self.book = {
        "id": self.sim + 1,
        "payoutMultiplier": 0.0,
        "events": [],
        "criteria": self.criteria,
    }
```

At the end of a round, if all win criteria are satisfied, the book is added to the **library**. For more details, see [BetMode](../gamestate_section/configuration_section/betmode_overview.md).

## Lookup Tables

The **payoutMultipler** attached to a **book** represents the final amount paid to the player, inclusive or *basegame* and *freegame* wins. The **LookUpTable** *csv* file is a summary of all simulation payouts. This provides a convenient way to calculate win distribution properties and Return To Player calculations. All lookup tables will be of the format:

| Simulation Number | Simulation Weight | Payout Multiplier |
| ----------------- | ----------------- | ------------------|
|       1           |          1        |        0.0        |
|       2           |          1        |        92.3       |
|       ...         |          ...      |        ...        |


All files generated from the Math Engine will have the prefix `lookUpTable_mode.csv`. This is the file consumed by the optimization algorithm, which has the effect of modifying the weight values, which are initially set to `1`. Optimized lookup tables will have the prefix `lookUpTable_mode_0.csv`