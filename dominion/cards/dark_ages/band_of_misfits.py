"""Band of Misfits — $5 Command card that plays a cheaper non-Command Action."""

from ..base_card import Card, CardCost, CardStats, CardType


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

        candidates: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                c = get_card(name)
            except ValueError:
                continue
            if not c.is_action or c.is_command:
                continue
            if c.cost.potions > 0 or c.cost.debt > 0:
                continue
            cost = game_state.get_card_cost(player, c)
            if cost >= my_cost:
                continue
            if not c.may_be_bought(game_state):
                continue
            candidates.append(c)

        choice = player.ai.choose_band_of_misfits_target(
            game_state, player, candidates
        )
        if not choice:
            return

        # Play the chosen card "as if" it were the Action.
        # Per official rules, Band of Misfits stays in play; the chosen card
        # is not actually moved here. We instantiate a fresh copy and resolve
        # its on_play, but treat it as Band of Misfits for in-play state.
        impostor = get_card(choice.name)
        impostor.on_play(game_state)
        game_state.fire_ally_play_hooks(player, impostor)
