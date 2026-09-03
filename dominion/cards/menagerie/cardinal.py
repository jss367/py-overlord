"""Cardinal - Action-Attack from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Cardinal(Card):
    """+$2. Each other player reveals the top 2 cards of their deck, Exiles
    one costing $3-$6 (their choice), and discards the rest.
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

                # The target Exiles exactly one card costing $3-$6 (their
                # choice) to their own Exile mat and discards the rest.
                eligible = [c for c in revealed if 3 <= c.cost.coins <= 6]
                exiled = None
                if eligible:
                    exiled = target.ai.choose_card_to_exile_for_cardinal(
                        game_state, target, eligible
                    )
                    if exiled not in eligible:
                        exiled = eligible[0]
                    target.exile.append(exiled)
                for c in revealed:
                    if c is exiled:
                        continue
                    game_state.discard_card(target, c)

            game_state.attack_player(
                other, attack_target, attacker=player, attack_card=self
            )
