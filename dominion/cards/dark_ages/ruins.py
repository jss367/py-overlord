"""Ruins variants used by Looter cards (Marauder/Cultist/Death Cart).

The five Ruins are all $0 Action-Ruins cards. They live as a single shuffled
"Ruins" supply pile. Players never directly buy from this pile — they receive
the top Ruin when a Looter card causes them to gain one.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class _BaseRuin(Card):
    """Common base: Action + Ruins type, $0, not buyable directly."""

    RUIN_NAME: str = "Ruins"

    def __init__(self, name: str, stats: CardStats | None = None):
        super().__init__(
            name=name,
            cost=CardCost(coins=0),
            stats=stats or CardStats(),
            types=[CardType.ACTION, CardType.RUINS],
        )

    def starting_supply(self, game_state) -> int:  # pragma: no cover - never bought
        return 0

    def may_be_bought(self, game_state) -> bool:  # pragma: no cover - never bought
        return False


class AbandonedMine(_BaseRuin):
    """+$1."""

    def __init__(self):
        super().__init__("Abandoned Mine", CardStats(coins=1))


class RuinedLibrary(_BaseRuin):
    """+1 Card."""

    def __init__(self):
        super().__init__("Ruined Library", CardStats(cards=1))


class RuinedMarket(_BaseRuin):
    """+1 Buy."""

    def __init__(self):
        super().__init__("Ruined Market", CardStats(buys=1))


class RuinedVillage(_BaseRuin):
    """+1 Action."""

    def __init__(self):
        super().__init__("Ruined Village", CardStats(actions=1))


class Survivors(_BaseRuin):
    """Look at the top 2 cards of your deck.

    Discard them or put them back on top in any order.
    """

    def __init__(self):
        super().__init__("Survivors")

    def play_effect(self, game_state):
        player = game_state.current_player

        revealed: list[Card] = []
        for _ in range(2):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        if player.ai.should_discard_survivors_reveal(game_state, player, list(revealed)):
            for card in revealed:
                game_state.discard_card(player, card)
            return

        ordered = player.ai.order_cards_for_topdeck(game_state, player, list(revealed))
        if set(ordered) != set(revealed) or len(ordered) != len(revealed):
            ordered = revealed
        # `order_cards_for_topdeck` returns top-to-bottom order.
        for card in reversed(ordered):
            player.deck.append(card)


class Ruins(_BaseRuin):
    """Generic Ruins placeholder kept for backward compatibility.

    The "Ruins" name is the supply-pile name. Individual gained Ruins are one
    of the five variant classes; this class only exists so that
    ``get_card("Ruins")`` continues to return a Card object (used by some
    callers / tests). Its on-play does nothing, matching the placeholder
    semantics that pre-existed in the codebase.
    """

    def __init__(self):
        super().__init__("Ruins")


# Convenience constants for setup.
RUIN_VARIANT_CLASSES = (
    AbandonedMine,
    RuinedLibrary,
    RuinedMarket,
    RuinedVillage,
    Survivors,
)

RUIN_VARIANT_NAMES = tuple(cls().name for cls in RUIN_VARIANT_CLASSES)
