Basegame:


# Freegame rules
Every tumle increments the gloabl multiplier by +1, which is persistent throughout the freegame
The global multiplier is applied to the tumble win as they are removed from the board
After all tumbles have completed: multiply the cumulative tumble win by multipliers on board 
(multipliers on board do not increment the gloabl mult)
If there is a multiplier symbol on the board, this is added to the gloabl multiplier before the final evaluation


# Notes
Due to the potential for symbols to tumble into the active board area, there is no upper limit on the number of freespis that can be awarded.
The total number of freespins is 2 * (number of Scatters on baord). To account for this the usual 'updateTotalFreeSpinAmount' function is overridden 
in the game_executables.py file.

# Event descritpion
"winInfo" Summarises winning combinations. Includes multipliers, symbol postiions, payInfo [passed for every tumble event]
"tumbleBanner" includes values from the cumulative tumble, with global mult applied
"setWin" this the result for the entire spin (from on Reveal to the next). Applied after board has stopped tumbling
"seTotalWin" the cumulative win for a round. In the base-game this will be equal to the setWin, but in the bonus it will incrementally increase 

