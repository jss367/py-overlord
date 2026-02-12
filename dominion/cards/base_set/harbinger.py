from ..base_card import Card, CardCost, CardStats, CardType


class Harbinger(Card):
    def __init__(self):
        super().__init__(
            name="Harbinger",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.discard:
            return
        choice = player.ai.choose_card_to_topdeck_from_discard(
            game_state, player, list(player.discard)
        )
        if choice and choice in player.discard:
            player.discard.remove(choice)
            player.deck.insert(0, choice)
