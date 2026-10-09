from ..base_card import Card, CardCost, CardStats, CardType
from ..supply_play import select_supply_action, supply_action_choices


class Overlord(Card):
    """Play another Action card from the supply costing up to 5 coins."""

    def __init__(self):
        super().__init__(
            name="Overlord",
            cost=CardCost(debt=8),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.COMMAND],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        from ..registry import get_card

        choices = supply_action_choices(game_state, player, 5)
        proxy = select_supply_action(
            game_state, player, choices, "choose_overlord_target", legacy_action=True
        )
        if proxy is None:
            return
        temp_card = get_card(proxy.name)
        game_state.play_supply_action(player, self, temp_card)
