from ..base_card import Card, CardCost, CardStats, CardType


class Procession(Card):
    def __init__(self):
        super().__init__(
            name="Procession",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        """Play a non-Duration Action from hand twice, trash it, gain Action costing exactly 1 more."""
        from ..registry import get_card

        player = game_state.current_player

        # Choose a non-Duration Action from hand
        actions = [c for c in player.hand if c.is_action and not c.is_duration]
        if not actions:
            return

        choice = player.ai.choose_action(game_state, actions + [None])
        if choice is None or choice not in player.hand:
            return

        # Remove from hand and play it twice
        player.hand.remove(choice)
        player.in_play.append(choice)

        choice.on_play(game_state)
        choice.on_play(game_state)

        # Trash the played card
        target_cost = choice.cost.coins + 1
        if choice in player.in_play:
            player.in_play.remove(choice)
        game_state.trash_card(player, choice)

        # Gain an Action card costing exactly 1 more
        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            candidate = get_card(name)
            if candidate.is_action and candidate.cost.coins == target_cost:
                options.append(candidate)

        if not options:
            return

        gain_choice = player.ai.choose_buy(game_state, options)
        if gain_choice is None or gain_choice.name not in game_state.supply:
            gain_choice = options[0]

        if game_state.supply.get(gain_choice.name, 0) > 0:
            game_state.supply[gain_choice.name] -= 1
            game_state.gain_card(player, gain_choice)
