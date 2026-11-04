# Cluster-based win game

Clusters of 5 or more like-symbols are removed from the board, and symbols above on the reelstrip
fall to fill their place.

#### Basegame:
6x5 cluster game. Minimum cluster is 5, pays scale with size, and are uncapped.
The base, Ante, and Hunt bars fill at 10 connections. Bonuses fill at 5.
3 scatters start See No Evil, 4 start Hear No Evil, 5+ start Speak No Evil.
Wilds are uncapped and may land in tumbles. Max win is 25,000x. Target RTP is 96.3%.

#### Freegame:
Same basegame rule, except grid positions have multipliers. Grid positions start in a 'deactivated' state. Once one win occurs,
the position is 'activated' starting with a 1x multiplier - for every winning cluster, the multiplier value at that position is increased by +1 for every winning position.
A minimum of 3 scatters are required for re-triggers


#### Notes:
Because of the separation between basegame and freegame types - there is an additional freespin entry check to check of the criteria requires a forced 
freespin condition. Otherwise, occurences of Scatter symbols tumbling onto the board during basegame criteria may appear.