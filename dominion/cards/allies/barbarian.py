from ..base_card import Card, CardCost, CardStats, CardType


class Barbarian(Card):
    """Implements the Barbarian attack from Allies."""

    def __init__(self):
        super().__init__(
            name="Barbarian",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        from ._rules import candidates, cheaper, effective_cost, gain

        player = game_state.current_player

        def attack(target):
            if not target.deck and target.discard:
                target.shuffle_discard_into_deck()
            if not target.deck:
                game_state.give_curse_to_player(target)
                return
            card = target.deck.pop()
            game_state.trash_card(target, card)
            cost = effective_cost(game_state, card)
            if cost.coins >= 3:
                choices = candidates(
                    game_state,
                    predicate=lambda c: (
                        cheaper(effective_cost(game_state, c), cost)
                        and bool(set(c.types) & set(card.types))
                    ),
                )
                gain(game_state, target, choices)
            else:
                game_state.give_curse_to_player(target)

        for target in game_state.opponents_in_order(player):
            game_state.attack_player(target, attack, attacker=player, attack_card=self)
