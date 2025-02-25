# Carrot MathEngine
### Powered by **CarrotRGS**

Welcome to the Carrot-MathEngine!
Your one-stop-shop for spectacular slots.


## Directory Structure
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

    tests/ # [**TBC**] Test cases for various win-types
    utils/ # [**TBC**] Useful functions to aid with file and game analysis
    uploads/ # [**TBC**] Data transformation and upload verification
    optimization/ # [**TBC**] Optimization algorithm
    docs/ # Markdown files

