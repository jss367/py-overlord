"""Cardinal - Action-Attack from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Cardinal(Card):
    """+$2. Each other player reveals top 2 cards of their deck. Exile any
    costing $3-$6, then they discard the rest.
    """

    def __init__(self):
        super().__init__(
            name="Cardinal",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        for other in game_state.players:
            if other is player:
                continue

            def attack_target(target):
                # Reveal top 2 cards
                revealed = []
                for _ in range(2):
                    if not target.deck and target.discard:
                        target.shuffle_discard_into_deck()
                    if not target.deck:
                        break
                    revealed.append(target.deck.pop())

                # Exile cards costing $3-$6 to the *target's* exile mat;
                # discard the rest.
                for c in revealed:
                    if 3 <= c.cost.coins <= 6:
                        target.exile.append(c)
                    else:
                        game_state.discard_card(target, c)

            game_state.attack_player(
                other, attack_target, attacker=player, attack_card=self
            )
