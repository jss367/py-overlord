"""Implementation of the Ironworks gainer."""

from ..base_card import Card, CardCost, CardStats, CardType


class Ironworks(Card):
    """Gain a card costing up to $4.

    If the gained card is an Action, +1 Action; if a Treasure, +$1; if a
    Victory card, +1 Card. A card of several types grants every matching
    bonus (Great Hall gives both +1 Action and +1 Card).
    """

    def __init__(self):
        super().__init__(
            name="Ironworks",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    @staticmethod
    def _default_gain(options):
        """Deterministic fallback: the priciest card, Actions first on a tie.

        The gain is not optional, so a strategy that declines still has to
        gain something."""

        return max(
            options,
            key=lambda c: (c.cost.coins, c.is_action, c.is_treasure, c.is_victory, c.name),
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        from dominion.ai.gain_context import FreeGainContext
        from ..gain_decisions import choose_free_gain, gain_menu, gain_selected, gained_card_types

        options = gain_menu(game_state, player, CardCost(coins=4))
        context = FreeGainContext.build(game_state, player, self.name, source_card=self)
        choice = choose_free_gain(game_state, player, options, self.name, context=context)
        gained = []
        gain_selected(game_state, player, choice, choices=options, source=self.name,
                      context=context, gain_observer=gained.append)
        if not gained:
            return
        actual = gained[0]
        action, treasure, victory = gained_card_types(game_state, player, actual)
        if action and not player.ignore_action_bonuses:
            player.actions += 1
        if treasure:
            player.coins += 1
        if victory:
            game_state.draw_cards(player, 1)
