# Maintaining printed coin classification

`dominion/cards/printed_coin_instructions.py` records the Capitalism decision for
all 485 registered printed Action names: 159 have a printed coin instruction and
326 do not. This is a classification audit, not a tactical or whole-card audit.
The two sets are disjoint and their union must match registered Actions; the
regression test requires an explicit classification when a new Action is added.

`GameState.is_treasure` reads this metadata rather than executable `CardStats`.
Changing stats for a Way, a conditional choice, or a later-turn callback must not
change the printed classification. Game decisions use the shared live Action,
Treasure and Command predicates. Heuristic estimates may still use printed
resources; legal menus are built from live types.

The [publisher's Renaissance rules](https://www.riograndegames.com/wp-content/uploads/2022/03/Dominion-Rules-Renaissance.pdf), page 8,
require an actual plus-coin instruction and apply the modifier everywhere during
the project owner's turn. Conditional choices, trash/discard payoffs, on-gain
instructions and next-turn bonuses count. Coffers, cost limits/reductions, coin
values without a plus instruction, moving pile tokens, receiving Boons and playing
another card do not. In particular, Coppersmith and Teacher do not qualify.

The explicit conditional/delayed pass includes Amulet, Aristocrat, Baron,
Bounty Hunter, Broker, Cabin Boy, Capital City, Caravan Guard, Change, Chariot Race,
City, Count, Courser, Courtier, Death Cart, Farmers' Market, Forager, Giant,
Harbor Village, Harvest, Ironmonger, Ironworks, Kitsune, Marchland, Mercenary,
Merchant, Mill, Mining Village, Minion, Miser, Moneylender, Opulent Castle, Pawn,
Pirate Ship, Poor House, Sacrifice, Sailor, Salvager, Samurai, Scrap, Secret Cave,
Secret Chamber, Souk, Spice Merchant, Steward, Storeroom, Storyteller, Stronghold,
Swamp Hag, Sycophant, Tournament, Town, Town Crier, Trade Route, Tribute,
Trusty Steed and Vault. Storyteller's missing initial coin bonus was corrected
separately from its classification.

Publisher references for the conditional/delayed pass include
[Adventures](https://www.riograndegames.com/wp-content/uploads/2015/01/DomAdventures2022.pdf),
[Intrigue](https://www.riograndegames.com/wp-content/uploads/2016/09/DomIntrigue.pdf),
[Dark Ages](https://www.riograndegames.com/wp-content/uploads/2022/03/Dominion-Rules-DarkAges.pdf),
[Hinterlands](https://www.riograndegames.com/wp-content/uploads/2022/05/Hinterlands2nd.pdf),
[Nocturne](https://www.riograndegames.com/wp-content/uploads/2022/03/Dominion-Rules-Nocturne.pdf),
[Allies](https://www.riograndegames.com/wp-content/uploads/2021/09/DomAllies.pdf),
[Plunder](https://www.riograndegames.com/wp-content/uploads/2022/08/DomPlunder.pdf), and
[Rising Sun](https://www.riograndegames.com/wp-content/uploads/2024/04/DomRisingSunRules.pdf).
Use current publisher text when changing a classification; executable coin
mutations alone are insufficient (for example, Carpenter and Modify mutate gain
limits, whereas Merchant and Harbor Village register deferred instructions).

| Expansion | Qualifies | Does not qualify |
| --- | ---: | ---: |
| Adventures | 13 | 22 |
| Alchemy | 1 | 8 |
| Allies | 16 | 29 |
| Base | 9 | 22 |
| Cornucopia | 9 | 18 |
| Dark Ages | 15 | 37 |
| Empires | 9 | 16 |
| Guilds | 1 | 11 |
| Hinterlands | 9 | 19 |
| Intrigue | 13 | 17 |
| Menagerie | 10 | 18 |
| Nocturne | 6 | 19 |
| Plunder | 10 | 17 |
| Promo | 2 | 9 |
| Prosperity | 11 | 9 |
| Renaissance | 6 | 16 |
| Rising Sun | 7 | 17 |
| Seaside | 12 | 22 |

Inheritance changes all Estates to Action–Command–Victory during its owner's
turn, including opponents' cards and Supply cards. It does not copy coin
metadata. The set-aside physical card is owned and scores normally, while each
Estate and target produce distinct plays. See the
[published rules and compatibility guide](../reports/strategies/capitalism-and-inheritance-rules-and-policy-compatibility.html)
for current evidence and the separate historical studies.
