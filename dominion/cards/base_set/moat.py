from ..base_card import Card, CardCost, CardStats, CardType


class Moat(Card):
    def __init__(self):
        super().__init__(
            name="Moat",
            cost=CardCost(coins=2),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def react_to_attack(self, game_state, player):
        if not player.ai.should_reveal_moat(game_state, player):
            return None
        game_state.log_callback(
            ("action", player.ai.name, "reveals Moat to block the attack", {})
        )
        return "block"
