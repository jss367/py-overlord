from ..base_card import Card, CardCost, CardStats, CardType


class Workshop(Card):
    def __init__(self):
        super().__init__(
            name="Workshop",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        """Gain a card costing up to 4 coins."""
        player = game_state.current_player

        # Find cards that can be gained
        possible_gains = [
            card
            for _name, card, _count in game_state._iter_gainable_supply_cards()
            if card.cost.coins <= 4
        ]

        # Let AI choose what to gain
        if possible_gains:
            chosen_card = player.ai.choose_buy(game_state, possible_gains)

            if chosen_card:
                # Gain the chosen card
                game_state.supply[chosen_card.name] -= 1
                game_state.gain_card(player, chosen_card)
