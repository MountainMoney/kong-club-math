Basegame:


# Freegame rules
Every tumble increments the global multiplier by +1, which is persistent throughout the freegame
The global multiplier is applied to the tumble win as they are removed from the board
After all tumbles have completed: multiply the cumulative tumble win by multipliers on board 
(multipliers on board do not increment the global mult)
If there is a multiplier symbol on the board, this is added to the global multiplier before the final evaluation


# Notes
Due to the potential for symbols to tumble into the active board area, there is no upper limit on the number of freespins that can be awarded.
The total number of freespins is 2 * (number of Scatters on board). To account for this the usual 'updateTotalFreeSpinAmount' function is overridden 
in the game_executables.py file.

# Event descriptions
"winInfo" Summarises winning combinations. Includes multipliers, symbol positions, payInfo [passed for every tumble event]
"tumbleBanner" includes values from the cumulative tumble, with global mult applied
"setWin" this the result for the entire spin (from on Reveal to the next). Applied after board has stopped tumbling
"seTotalWin" the cumulative win for a round. In the base-game this will be equal to the setWin, but in the bonus it will incrementally increase 

