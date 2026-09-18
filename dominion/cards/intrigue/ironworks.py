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

        options = [
            card
            for _name, card, _count in game_state._iter_gainable_supply_cards()
            if game_state.get_card_cost(player, card) <= 4
            and card.cost.potions == 0
            and card.cost.debt == 0
        ]
        if not options:
            return

        # The choice belongs to the player: Ironworks' three bonuses make the
        # right pick board- and turn-dependent, so route it through the AI
        # exactly as Workshop does.
        gained = player.ai.choose_buy(game_state, list(options))
        if gained is None or gained.name not in {c.name for c in options}:
            gained = self._default_gain(options)

        if game_state.supply.get(gained.name, 0) <= 0:
            return
        game_state.supply[gained.name] -= 1
        game_state.log_callback(
            ("supply_change", gained.name, -1, game_state.supply[gained.name])
        )
        actual = game_state.gain_card(player, gained)
        if actual is None:
            return

        if actual.is_action:
            player.actions += 1
        if actual.is_treasure:
            player.coins += 1
        if actual.is_victory:
            game_state.draw_cards(player, 1)
