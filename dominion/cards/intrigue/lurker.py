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
        from ..registry import get_card

        player = game_state.current_player

        trashable_actions: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action:
                continue
            if not card.may_be_bought(game_state):
                continue
            trashable_actions.append(card)

        gainable_actions: list[Card] = [
            c for c in game_state.trash if c.is_action
        ]

        can_trash = bool(trashable_actions)
        can_gain = bool(gainable_actions)
        if not can_trash and not can_gain:
            return

        mode = player.ai.choose_lurker_mode(
            game_state, player, can_trash=can_trash, can_gain=can_gain
        )
        if mode == "gain" and not can_gain:
            mode = "trash"
        elif mode == "trash" and not can_trash:
            mode = "gain"

        if mode == "trash":
            chosen = player.ai.choose_action_to_trash_from_supply(
                game_state, player, trashable_actions
            )
            if chosen is None or game_state.supply.get(chosen.name, 0) <= 0:
                return
            game_state.supply[chosen.name] -= 1
            game_state.log_callback(
                ("supply_change", chosen.name, -1, game_state.supply[chosen.name])
            )
            game_state.trash_card(player, chosen)
            return

        # mode == "gain"
        chosen = player.ai.choose_action_to_gain_from_trash(
            game_state, player, gainable_actions
        )
        if chosen is None or chosen not in game_state.trash:
            return
        game_state.trash.remove(chosen)
        player.discard.append(chosen)
        chosen.on_gain(game_state, player)
