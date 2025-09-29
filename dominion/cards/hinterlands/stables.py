from ..base_card import Card, CardCost, CardStats, CardType


class Stables(Card):
    def __init__(self):
        super().__init__(
            name="Stables",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        treasures = [card for card in player.hand if card.is_treasure]
        if not treasures:
            return

        choice = min(treasures, key=self._discard_priority)
        player.hand.remove(choice)
        game_state.discard_card(player, choice)

        game_state.draw_cards(player, 3)
        player.actions += 1

    @staticmethod
    def _discard_priority(card):
        if card.name == "Copper":
            return (0, card.name)
        if card.name == "Silver":
            return (1, card.name)
        return (2, card.cost.coins, card.name)
