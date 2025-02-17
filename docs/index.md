# Zuck-Engine&trade;
### Powered by **CarrotRGS**

Welcome to the Zuck-Engine!
Your one-stop-shop for slots.


## Directory
    src/ 
        calculations/ # Board and Symbol setup, various win-type game logic
        config/ # Creates configuration files required by the RGS, frontend and optimization algorithm
        events/ # Data structures passed between math-engine and frontend engine
        executables/ # Commonly used groupings of game logic and events
        state/ # Tracks the game-state of all simulations 
        wins/ # Wallet manager handling various win-criteria
        write_data/ # Handles writing simulation data, compression and force-files

    games/
        0_0_cluster # Sample cascading cluster-wins game
        0_0_lines # Basic win-lines example game
        0_0_ways # Basic ways-wins example game
        0_0_scatter # Pay-anywhere cascading example game
        0_0_expwilds # Example of expanding Wild-reel game, with prize-collection feature game

    test/ # [**TBC**] Test cases for various win-types
    utils/ # [**TBC**] Useful functions to aid with file and game analysis
    uplods/ # [**TBC**] Data transformation and upload verification
    optimization/ # [**TBC**] Optimization algorithm
    docs/ # Markdown files


## Commands
* `mkdocs new [dir-name]` - Create a new project.
* `mkdocs serve` - Start the live-reloading docs server.
* `mkdocs build` - Build the documentation site.
* `mkdocs -h` - Print help message and exit.