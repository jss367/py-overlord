from ..base_card import Card, CardCost, CardStats, CardType
from dominion.ai import tactical_defaults


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

        choices = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if (
                card.is_action
                and not card.is_command
                and not card.cost.debt
                and not card.cost.potions
                and game_state.get_card_cost(player, card) <= 5
            ):
                choices.append(card)
        if not choices:
            return
        hook = getattr(player.ai, "choose_overlord_target", None)
        if hook is not None:
            proxy = hook(game_state, player, choices)
        else:
            # Compatibility with small AIs that only implement generic choices.
            proxy = player.ai.choose_action(game_state, choices + [None])
            if proxy is None:
                proxy = tactical_defaults.choose_overlord_target(player, choices)
        if proxy is None or proxy.name not in {card.name for card in choices}:
            proxy = tactical_defaults.choose_overlord_target(player, choices)
        temp_card = get_card(proxy.name)
        player.in_play.append(temp_card)
        temp_card.on_play(game_state)
        game_state.fire_ally_play_hooks(player, temp_card)
        if temp_card in player.in_play:
            player.in_play.remove(temp_card)
