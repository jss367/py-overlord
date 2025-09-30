"""Implementation of the Armory gainer."""

from ..base_card import Card, CardCost, CardStats, CardType


class Armory(Card):
    def __init__(self):
        super().__init__(
            name="Armory",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        affordable: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins <= 4:
                affordable.append(card)

        if not affordable:
            return

        choice = player.ai.choose_buy(game_state, affordable + [None])
        if not choice:
            return

        if game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice, to_deck=True)
