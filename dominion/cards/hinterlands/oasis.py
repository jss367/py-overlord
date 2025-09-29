from ..base_card import Card, CardCost, CardStats, CardType


class Oasis(Card):
    def __init__(self):
        super().__init__(
            name="Oasis",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, cards=1, coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        discard = min(player.hand, key=self._discard_priority)
        player.hand.remove(discard)
        game_state.discard_card(player, discard)

    @staticmethod
    def _discard_priority(card):
        if card.name == "Curse":
            return (0, card.name)
        if card.is_victory and not card.is_action:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.name)
        return (3, card.cost.coins, card.name)
