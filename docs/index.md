# Carrot Math Engine
### Powered by **CarrotRGS**

**Welcome to the Carrot-Math-Engine!**

This engine provides a framework for creating and optimizing slot games, and outputs all files in a format agreeable to the Carrot RGS. This engine is used to define game rules, implement game logic, optimize win-distributions, generate compressed simulation results and perform statistical analysis on custom-defined events. By using a discrete set of outcomes, we can enforce strict control on game mechanics and hit-rates, without the need to explicitly *solve* potentially complex mathematical models.


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
        0_0_expwilds # Example of expanding Wild-reel game, and additional prize-collection feature game

    utils/ # Useful functions to aid with file and game analysis
        analysis/ # Construct and analyze basic properties of win distributions
        game_analytics/ # Use recorded events, paytable and lookup-tables to generate basic hit-rate and simulation properties
        
    uploads/ # Data upload process for uploading game-files to S3 bucket
    optimization_program/ # Optimization algorithm (Rust)
    tests/ # [**TBC**] Unit tests for win-functions
    docs/ # Markdown files

