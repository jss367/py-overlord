from ..base_card import Card, CardCost, CardStats, CardType


class Embassy(Card):
    def __init__(self):
        super().__init__(
            name="Embassy",
            cost=CardCost(coins=5),
            stats=CardStats(cards=5),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if len(player.hand) <= 3:
            return

        cards = sorted(player.hand, key=self._discard_priority)
        for card in cards[:3]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        from ..registry import get_card

        for other in game_state.players:
            if other is player:
                continue
            if game_state.supply.get("Silver", 0) <= 0:
                break
            game_state.supply["Silver"] -= 1
            game_state.gain_card(other, get_card("Silver"))

    @staticmethod
    def _discard_priority(card):
        if card.name == "Curse":
            return (0, card.name)
        if card.is_victory and not card.is_action:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.name)
        if card.is_treasure:
            return (3, card.cost.coins, card.name)
        return (4, card.cost.coins, card.name)
