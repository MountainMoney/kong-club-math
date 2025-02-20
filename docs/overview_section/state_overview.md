# The State Machine

## Introduction
When initializing a simulation batch, the **GameState** class serves as a central hub that manages all simulation aspects, including:

- Simulation parameters
- All game modes
- Configuration settings
- Simulation results
- Output files

This class acts as a super-class, ensuring shared components across all simulations. The entry point for all game simulations is the `run.py` file, which sets up parameters through the [Config](general_config.md) class and initializes a [GameState](gamestate_overview.md) object. The **GameState** handles crucial aspects such as:

## Simulation Configuration
- Compression
- Tracing
- Multithreading
- Output files
- Cumulative wins

## Game Configuration
- Bet modes
- Paytable
- Symbols
- Reelsets

These **global `GameState` attributes** remain consistent across all games, modes, and simulations. When a simulation runs, `run_spin()` creates a sub-instance of the **General GameState**, allowing modifications to game data through the `self` object.

### Example Simulation Execution
When a simulation is executed, key game events modify the state:

```python
self.draw_board()
win_data = self.get_lines()
self.emit_linewin_events()
```

- `self.draw_board()`: Generates a random board state.
- `self.get_lines()`: Evaluates winning paylines.
- `self.emit_linewin_events()`: Triggers game events based on results.

For a deeper dive into executables and state modifications, see [GameState](gamestate_run.md/). The central idea is that the **GameState** represents the current state of the simulation. And components within this state are modified directly. This reduces the need to be passing objects back and forth between functions when writing game logic.

## Class Inheritance

### Why Use Class Inheritance?
Class inheritance ensures flexibility, allowing developers to access core functions while customizing specific behaviors for each game. Core functions are found in the [Source Files](win_manager.md) section and can be overridden at the game level.

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

Example: Updating free spins based on Scatters:
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

Each simulation generates a **book**, which is stored in a **library** attached to the global **GameState** object.

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

At the end of a round, if all win criteria are satisfied, the book is added to the **library**. For more details, see [BetMode](betmode_overview/).

