"""Hostelry - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Hostelry(Card):
    """+1 Card +2 Actions. When you gain this, you may discard any number of
    Treasures for +1 Horse each.
    """

    def __init__(self):
        super().__init__(
            name="Hostelry",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        from ..registry import get_card

        if not player.hand:
            return

        treasures_in_hand = [c for c in player.hand if c.is_treasure]
        if not treasures_in_hand:
            return

        chosen = player.ai.choose_treasures_to_discard_for_hostelry(
            game_state, player, list(treasures_in_hand)
        )
        if not chosen:
            return

        for card in chosen:
            if card not in player.hand:
                continue
            if game_state.supply.get("Horse", 0) <= 0:
                break
            player.hand.remove(card)
            game_state.discard_card(player, card)
            game_state.supply["Horse"] -= 1
            game_state.gain_card(player, get_card("Horse"))
