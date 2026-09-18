"""Implementation of the Inventor cost reducer."""

from ..base_card import Card, CardCost, CardStats, CardType


class Inventor(Card):
    def __init__(self):
        super().__init__(
            name="Inventor",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        choices = []
        for _name, card, _count in game_state._iter_gainable_supply_cards():

            # Inventor should respect existing cost modifiers (including other
            # Inventors played earlier in the turn). ``get_card_cost`` applies the
            # player's current reductions, so we use it rather than the printed
            # cost on the pile.
            if game_state.get_card_cost(player, card) > 4:
                continue

            # Cards with potion costs cannot be gained by Inventor, matching the
            # official Workshop-style rules text.
            if card.cost.potions > 0 or card.cost.debt > 0:
                continue

            choices.append(card)

        if choices:
            chosen = player.ai.choose_buy(game_state, choices)
            gain = chosen if chosen in choices else max(choices, key=lambda c: (c.cost.coins, c.name))
            gained = game_state.take_top_supply_card(game_state.supply_pile_key(gain.name))
            if gained is not None:
                game_state.gain_card(player, gained)

        player.cost_reduction += 1
