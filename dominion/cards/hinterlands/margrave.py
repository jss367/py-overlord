from ..base_card import Card, CardCost, CardStats, CardType


class Margrave(Card):
    def __init__(self):
        super().__init__(
            name="Margrave",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3, buys=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack(target):
            game_state.draw_cards(target, 1)
            while len(target.hand) > 3:
                card = min(target.hand, key=self._discard_priority)
                target.hand.remove(card)
                game_state.discard_card(target, card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack)

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
