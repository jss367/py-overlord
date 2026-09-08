from ..base_card import Card, CardCost, CardStats, CardType


class Lurker(Card):
    """+1 Action. Choose: trash an Action from supply, OR gain an Action from trash."""

    def __init__(self):
        super().__init__(
            name="Lurker",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..allies._rules import candidates, select_modes

        player = game_state.current_player
        trashable = candidates(game_state, predicate=lambda c: c.is_action)
        gainable = [c for c in game_state.trash if c.is_action]
        default = player.ai.choose_lurker_mode(
            game_state, player, can_trash=bool(trashable), can_gain=bool(gainable)
        )
        for mode in select_modes(
            game_state, player, self, ["trash", "gain"], [default]
        ):
            if mode == "trash":
                if not trashable:
                    continue
                choice = player.ai.choose_action_to_trash_from_supply(
                    game_state, player, trashable
                )
                if choice not in trashable:
                    choice = trashable[0]
                pile = game_state._resolve_changeling_pile_name(choice)
                game_state.supply[pile] -= 1
                if pile in game_state.pile_order:
                    game_state.pile_order[pile].pop()
                game_state.trash_card(player, choice)
            else:
                # The first mode may have just added the desired card to the trash.
                gainable = [c for c in game_state.trash if c.is_action]
                if not gainable:
                    continue
                choice = player.ai.choose_action_to_gain_from_trash(
                    game_state, player, gainable
                )
                if choice not in gainable:
                    choice = gainable[0]
                game_state.trash.remove(choice)
                game_state.gain_card(player, choice, from_supply=False)
