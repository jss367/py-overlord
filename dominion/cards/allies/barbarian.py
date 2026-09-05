from ..base_card import Card, CardCost, CardStats, CardType


def _costs_less(cost: CardCost, than: CardCost) -> bool:
    """Dominion "cheaper": no cost component higher, at least one lower."""
    return (
        cost.coins <= than.coins
        and cost.potions <= than.potions
        and cost.debt <= than.debt
        and cost.comparison_tuple() != than.comparison_tuple()
    )


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
        from ..registry import get_card

        player = game_state.current_player

        def attack_target(target):
            # Ensure the target has a card to reveal
            if not target.deck and target.discard:
                target.shuffle_discard_into_deck()
            if not target.deck:
                game_state.give_curse_to_player(target)
                return

            revealed = target.deck.pop()
            cost = revealed.cost
            game_state.trash_card(target, revealed)

            if cost.coins >= 3:
                shared_types = set(revealed.types)
                candidates: list[Card] = []
                for name, count in game_state.supply.items():
                    if count <= 0:
                        continue
                    card = get_card(name)
                    if _costs_less(card.cost, cost) and shared_types.intersection(
                        card.types
                    ):
                        candidates.append(card)
                if candidates:
                    # The attacked player picks which qualifying card to gain;
                    # the gain is mandatory, so fall back to the priciest.
                    gain = target.ai.choose_buy(game_state, candidates + [None])
                    if gain is None or gain not in candidates:
                        gain = max(candidates, key=lambda c: (c.cost.coins, c.name))
                    game_state.supply[gain.name] -= 1
                    game_state.gain_card(target, gain)
            else:
                game_state.give_curse_to_player(target)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
