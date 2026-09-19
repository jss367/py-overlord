from ..base_card import Card, CardCost, CardStats, CardType


class Swindler(Card):
    def __init__(self):
        super().__init__(
            name="Swindler",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        """Each other player trashes top card; attacker chooses same-cost replacement."""
        from ..allies._rules import candidates, effective_cost

        player = game_state.current_player

        def attack_target(target):
            drawn = target.draw_cards(1)
            if not drawn:
                return
            card = drawn[0]
            target.hand.remove(card)
            trashed_cost = effective_cost(game_state, card)
            game_state.trash_card(target, card)
            options = candidates(
                game_state,
                predicate=lambda c: effective_cost(game_state, c) == trashed_cost,
            )
            if not options:
                return
            choice = player.ai.choose_swindler_replacement(
                game_state, player, target, options
            )
            if choice not in options:
                choice = options[0]
            gained = game_state.take_top_supply_card(
                game_state.supply_pile_key(choice.name)
            )
            if gained is not None:
                game_state.gain_card(target, gained)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
