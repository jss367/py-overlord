"""Implementation of Saboteur (1E)."""

from ..base_card import Card, CardCost, CardStats, CardType


class Saboteur(Card):
    """Each other player reveals cards from the top of their deck until
    revealing one costing $3 or more. They trash that card and may gain
    a card costing up to $2 less. They discard the other revealed cards."""

    def __init__(self):
        super().__init__(
            name="Saboteur",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            revealed_others: list[Card] = []
            trashed_cost: int | None = None

            while True:
                if not target.deck and target.discard:
                    target.shuffle_discard_into_deck()
                if not target.deck:
                    break
                top = target.deck.pop()
                if top.cost.coins >= 3:
                    trashed_cost = top.cost.coins
                    game_state.trash_card(target, top)
                    break
                else:
                    revealed_others.append(top)

            # Discard everything else revealed.
            for card in revealed_others:
                game_state.discard_card(target, card)

            if trashed_cost is None:
                return

            # The target may gain a card costing up to (trashed_cost - 2).
            max_cost = trashed_cost - 2
            if max_cost < 0:
                return

            chosen = target.ai.choose_card_to_gain_for_saboteur(
                game_state, target, max_cost
            )
            if chosen is None:
                return
            if game_state.supply.get(chosen.name, 0) <= 0:
                return
            game_state.supply[chosen.name] -= 1
            game_state.log_callback(
                ("supply_change", chosen.name, -1, game_state.supply[chosen.name])
            )
            game_state.gain_card(target, chosen)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
