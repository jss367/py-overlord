# Dark Ages Card Implementation Review

This document reviews the current state of the Dominion: Dark Ages cards implemented in
`py-overlord` as of commit HEAD. It highlights which cards exist in the codebase and the
major deviations from the official card rules that were observed.

## Implemented cards and issues

| Card | Location | Issues observed |
| --- | --- | --- |
| Armory | `dominion/cards/dark_ages/armory.py` | Prompts the player to gain any card costing up to $4 to the top of their deck, matching the official effect. |
| Beggar | `dominion/cards/dark_ages/beggar.py` | Gains three Coppers to hand and supports the Reaction to discard for two Silvers (one to hand, one to deck) when another player plays an Attack. |
| Count | `dominion/cards/dark_ages/count.py` | Implements both stages of choices from the real card, letting the player pick among the official options in each set. |
| Forager | `dominion/cards/dark_ages/forager.py` | Trashing is optional and the coin bonus equals the number of differently named Treasures in the trash, as in the official rules. |
| Ironmonger | `dominion/cards/dark_ages/ironmonger.py` | Revealed card bonuses are correct and the player decides whether to discard the revealed card. |
| Marauder | `dominion/cards/dark_ages/marauder.py` | Gains Spoils and distributes Ruins from the shared piles, properly decrementing supply counts. |
| Poor House | `dominion/cards/dark_ages/poor_house.py` | Effect matches the real card. |
| Rats | `dominion/cards/dark_ages/rats.py` | Gains another Rats if available and forces the player to trash a non-Rats card when possible. |
| Rebuild | `dominion/cards/dark_ages/rebuild.py` | Names a card, reveals until a different Victory card appears, trashes it, and gains a Victory card costing up to $3 more. |
| Ruins | `dominion/cards/dark_ages/ruins.py` | Implements the full Ruins pile (Abandoned Mine, Ruined Market, Ruined Library, Ruined Village, Survivors) with their individual effects. |
| Shelters (Hovel, Necropolis, Overgrown Estate) | `dominion/cards/dark_ages/shelters.py` | Adds Hovel's "trash on gaining a Victory card" reaction and Overgrown Estate's on-trash draw. |
| Spoils | `dominion/cards/dark_ages/spoils.py` | Returns to the pile after play and gains are tracked through the shared supply. |

## Missing Dark Ages cards

The following Dark Ages cards (including special non-supply cards) are not currently
implemented in the repository:

- Altar
- Band of Misfits
- Bandit Camp
- Catacombs
- Counterfeit
- Cultist
- Death Cart
- Feodum
- Fortress
- Graverobber
- Hermit (and its associated Madman non-supply card)
- Hunting Grounds
- Junk Dealer
- Knights split pile (Dame Anna, Dame Josephine, Dame Molly, Dame Natalie, Dame Sylvia, Sir Bailey, Sir Destry, Sir Martin, Sir Michael, Sir Vander)
- Market Square
- Mystic
- Pillage
- Procession
- Rogue
- Sage
- Scavenger
- Squire
- Storeroom
- Urchin (and its associated Mercenary non-supply card)
- Vagrant
- Wandering Minstrel

These omissions mean the Dark Ages expansion is far from complete and many key mechanics
(e.g., Knights, on-trash effects, split piles, and specialized gainers) are unavailable.

## Summary

Only a subset of the kingdom cards and related components from Dark Ages are present, but the
implemented cards now mirror their official rules, including choice prompts, reactions, supply
management, and on-trash abilities. Completing the expansion still requires implementing the
missing cards listed above to cover mechanics such as Knights, on-trash gainers, split piles, and
special non-supply cards.
