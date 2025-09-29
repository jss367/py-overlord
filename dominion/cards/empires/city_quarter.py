from ..base_card import Card, CardCost, CardStats, CardType


class CityQuarter(Card):
    def __init__(self):
        super().__init__(
            name="City Quarter",
            cost=CardCost(coins=8),
            stats=CardStats(actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        actions_in_hand = sum(1 for card in player.hand if card.is_action)
        if actions_in_hand:
            game_state.draw_cards(player, actions_in_hand)
