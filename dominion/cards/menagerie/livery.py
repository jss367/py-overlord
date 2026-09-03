"""Livery - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Livery(Card):
    """+$3. This turn, when you gain a card costing $4+, gain a Horse.

    Terminal: the printed card gives no +Action.
    """

    def __init__(self):
        super().__init__(
            name="Livery",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION],
        )

    def get_additional_non_supply_piles(self) -> dict[str, int]:
        from .supplies import HORSE_PILE_COUNT

        return {"Horse": HORSE_PILE_COUNT}

    def play_effect(self, game_state):
        # Track that there's a Livery in play; the gain hook handles the
        # Horse-grant trigger.
        pass
