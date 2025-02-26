# Output files

All relevant output files are automatically generated within the `game/library/` directories. If the required sub-directories do not exist, the will be automatically generated.

### Books

The primary data file output when simulations are run are the book files. These contain summary simulation information such as the final payout multiplier, basegame and freegame win contributions, the simulation criteria and simulation events. The contents of `book.events` is the information returned by the RGS `play/` API response. 
