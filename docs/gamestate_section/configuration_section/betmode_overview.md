All valid bet-modes are defined in the array `self.bet_modes = [ ...]` 
The `BetMode` class is an important configuration for when setting up game the behaviour of a game. A full description of all features is defined [here](../../source_section/config_info.md)

This class is used to set maximum win amounts, RTP, bet cost, and distribution conditions. Additional noteworthy tags are:

1. `auto_close_disabled`
    * When this flag is `False` (default) the RGS endpoint API `/endround` is called automatically to close out the bet for efficiency. When the bet is closed however, the player cannot resume their bet. It may be desirable in bonus modes for example, to set this flag to `True` so that the player can resume interrupted play even if the payout is `0`. This means that the front-end will have to manually close out the bet in this instance.
2. `is_feature`
    * When this flag is true, it tells the frontend to preserve the current bet-mode without the need for player interaction. So if the player changes to `alt_mode` where this mode has `is_feature = True`, every time the spin/bet button is pressed, it will call the last selected bet-mode. Unlike in bonus games, where the player needs to confirm the bet-mode choice after each round completion.
3. `is_buybonus`
    * This is a flag used for the frontend framework to determine if the mode has been purchased directly (and hence may require a change in assets).
