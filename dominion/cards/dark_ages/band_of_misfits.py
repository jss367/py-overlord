"""Band of Misfits — $5 Command card that plays a cheaper non-Command Action."""

from ..base_card import Card, CardCost, CardStats, CardType
from ..supply_play import select_supply_action, supply_action_choices


class BandOfMisfits(Card):
    """Play a non-Command Action card from the supply costing less than this,
    leaving it there.
    """

    def __init__(self):
        super().__init__(
            name="Band of Misfits",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.COMMAND],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        my_cost = game_state.get_card_cost(player, self)

        candidates = supply_action_choices(game_state, player, my_cost - 1)
        choice = select_supply_action(
            game_state, player, candidates, "choose_band_of_misfits_target"
        )
        if not choice:
            return

        # Play the chosen card "as if" it were the Action.
        # Per official rules, Band of Misfits stays in play; the chosen card
        # is not actually moved here. We instantiate a fresh copy and resolve
        # its on_play, but treat it as Band of Misfits for in-play state.
        impostor = get_card(choice.name)
        if not impostor.is_action:
            # Live Action types (Enlightenment Treasures) require the shared
            # substitution, Way offer and Action-play bookkeeping.
            game_state.play_action_indirectly(player, impostor)
            return
        impostor.on_play(game_state)
        game_state.fire_ally_play_hooks(player, impostor)
