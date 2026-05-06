"""Magpie (Adventures) — $4 Action."""

from ..base_card import Card, CardCost, CardStats, CardType


class Magpie(Card):
    def __init__(self):
        super().__init__(
            name="Magpie",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return
        top = player.deck[-1]
        if top.is_treasure:
            player.deck.pop()
            player.hand.append(top)
        if top.is_action or top.is_victory:
            if game_state.supply.get("Magpie", 0) > 0:
                game_state.supply["Magpie"] -= 1
                game_state.gain_card(player, get_card("Magpie"))
