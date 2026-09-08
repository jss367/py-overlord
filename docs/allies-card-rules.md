# Allies card rules and regression coverage

The implementation follows the publisher’s [November 2023 Allies rulebook](https://www.riograndegames.com/wp-content/uploads/2021/09/DomAllies.pdf), including its card images and clarifications. The scope is the 49 official Kingdom cards and 23 Ally landscapes. The Courier correction from [pull request 348](https://github.com/jss367/py-overlord/pull/348) is included through the merged main branch.

The corrected behavior includes:

- Printed costs, card types, resources, scoring, and the nine actual Liaisons. Each rotating pile contains four copies of each member at every player count.
- Physical pile rotation and returns, including Battle Plan rotating piles from other expansions. Gains use the exposed card, current costs, and all coin, Potion, and Debt components.
- Missing or incorrect card effects, including Innkeeper’s third option, Sunken Treasure’s Action gain, Lich’s skipped turns and trash recovery, and Stronghold’s immediate money or delayed draw.
- Ally triggers at the appropriate play, gain, Buy-phase, shuffle, cleanup, or turn-end event. Peaceful Cult correctly resolves at the **start of the Buy phase**; its spending happens before trash reactions.
- Duration cards retained until their instructions finish, completed cards remaining in play until cleanup, and ownership of cards set aside by Contract and Royal Galley. Repeated plays retain their delayed instructions and required multipliers.
- Gain effects recorded per play for Galleria, Guildmaster, and Skirmisher, with turn-end expiration. Skirmisher checks attack protection when played and subsequently triggers on Attack gains.
- Elder’s optional extra choices, resolved in printed order, including choice cards from other expansions. The permission belongs to the particular played card and expires at turn end.

## Strategy choices

The shared rules helpers validate choices and supply deterministic defaults. Existing strategies continue to work. Optional rotation defaults to declining; mandatory gains and trashes fall back to a legal selection when an AI declines or returns an invalid choice.

An AI or strategy can implement `choose_allies_option(state, player, reason, options, default)` for individual choices, and `choose_card_modes(state, player, card, options, minimum, maximum, defaults)` for printed lists of abilities. Returning only the required number of modes declines Elder’s optional extra. Existing card-specific decision hooks still supply defaults where available.

These defaults implement legal decisions; they are not claims of optimal play. Previously measured strategy results may change because the game rules have changed.

## Tests

[Printed-rule regressions](../tests/test_allies_printed_rules.py) cover metadata and the effects identified in the review. [Interaction regressions](../tests/test_allies_interactions.py) cover rotations and returns, repeated Durations, ownership, gain triggers, attack protection, actual shuffles, Elder choices, and skipped or extra turns. Existing tests that asserted incorrect rules have been corrected as well.

Run the complete suite and required lint check from the repository root:

```sh
python -m pytest -q
python -m ruff check . --select E9,F63,F7,F82
```

This coverage does not certify every possible combination across all Dominion expansions.
