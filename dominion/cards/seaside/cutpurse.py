from ..base_card import Card, CardCost, CardStats, CardType


class Cutpurse(Card):
    """Action-Attack ($4): +$2. Each other player discards a Copper
    (or reveals a hand with no Copper).
    """

    def __init__(self):
        super().__init__(
            name="Cutpurse",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            for card in target.hand:
                if card.name == "Copper":
                    target.hand.remove(card)
                    game_state.discard_card(target, card)
                    return

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
