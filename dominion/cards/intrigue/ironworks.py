"""Implementation of the Ironworks gainer."""

from ..base_card import Card, CardCost, CardStats, CardType


class Ironworks(Card):
    def __init__(self):
        super().__init__(
            name="Ironworks",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        gain_options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins <= 4:
                gain_options.append(card)

        if not gain_options:
            return

        gain_options.sort(key=lambda c: (c.is_action, c.is_treasure, c.is_victory, c.cost.coins), reverse=True)
        gained = gain_options[0]
        game_state.supply[gained.name] -= 1
        actual = game_state.gain_card(player, gained)

        if actual.is_action:
            player.actions += 1
        if actual.is_treasure:
            player.coins += 1
        if actual.is_victory:
            game_state.draw_cards(player, 1)
