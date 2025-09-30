from ..base_card import Card, CardCost, CardStats, CardType


class Mandarin(Card):
    def __init__(self):
        super().__init__(
            name="Mandarin",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.hand:
            return

        choice = min(player.hand, key=self._topdeck_priority)
        player.hand.remove(choice)
        player.deck.insert(0, choice)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        treasures = [card for card in player.in_play if card.is_treasure]
        for card in reversed(treasures):
            player.in_play.remove(card)
            player.deck.insert(0, card)

    @staticmethod
    def _topdeck_priority(card):
        if card.name == "Curse":
            return (0, card.name)
        if card.is_victory and not card.is_action:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.name)
        return (3, card.cost.coins, card.name)
