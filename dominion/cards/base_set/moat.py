from ..base_card import Card, CardCost, CardStats, CardType


class Moat(Card):
    """Action - Reaction ($2): +2 Cards.

    When another player plays an Attack card, you may first reveal this from
    your hand to be unaffected by it.
    """

    def __init__(self):
        super().__init__(
            name="Moat",
            cost=CardCost(coins=2),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def react_to_attack(self, game_state, player, attacker, attack_card) -> bool:
        """Reveal Moat to block the attack."""

        # The AI hook gives strategies a chance to opt out (defaults to True).
        if not player.ai.should_reveal_moat(game_state, player):
            return False

        game_state.log_callback(
            (
                "action",
                player.ai.name,
                "reveals Moat to block the attack",
                {"attacker": attacker.ai.name if attacker else None},
            )
        )
        return True
