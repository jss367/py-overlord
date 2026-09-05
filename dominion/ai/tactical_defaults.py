"""Shared tactical baselines for AIs and strategy-specific overrides.

These rank an already legal menu; card effects remain responsible for legality.
They are intentionally modest heuristics, not claims of optimal card play.
"""

from dominion.cards.base_card import Card


def choose_overlord_target(player, choices: list[Card]) -> Card | None:
    """Prefer action support when needed, otherwise immediate draw and money."""
    terminals = sum(c.is_action and c.stats.actions == 0 for c in player.hand)
    needs_actions = terminals > player.actions

    def score(card: Card) -> tuple:
        return (
            needs_actions and card.stats.actions >= 2,
            card.stats.cards * 2 + card.stats.coins,
            card.stats.actions,
            card.stats.buys,
            card.cost.coins,
            card.name,
        )

    return max(choices, key=score, default=None)


def choose_quartermaster_gain(choices: list[Card]) -> Card | None:
    """Prefer non-Victory, non-junk gains, then cost and printed resources."""
    return max(
        choices,
        key=lambda c: (
            c.name not in {"Curse", "Copper"} and not c.is_ruins,
            not c.is_victory,
            c.cost.coins,
            c.stats.cards,
            c.stats.actions,
            c.stats.coins,
            c.name,
        ),
        default=None,
    )


def quartermaster_take_all(mat: list[Card]) -> bool:
    """Baseline collection cadence: gain twice, then collect; overridable."""
    return len(mat) >= 2
