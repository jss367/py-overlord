from ..base_card import Card, CardCost, CardStats, CardType


class PearlDiver(Card):
    """Action ($2): +1 Card, +1 Action. Look at the bottom card of your deck.
    You may put it on top.
    """

    def __init__(self):
        super().__init__(
            name="Pearl Diver",
            cost=CardCost(coins=2),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return

        bottom = player.deck[0]

        # Heuristic: topdeck Action or expensive Treasure; otherwise leave it.
        if bottom.is_action or (bottom.is_treasure and bottom.cost.coins >= 3):
            player.deck.pop(0)
            player.deck.append(bottom)
