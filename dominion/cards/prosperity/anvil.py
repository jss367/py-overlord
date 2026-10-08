from ..base_card import Card, CardCost, CardStats, CardType


class Anvil(Card):
    """Treasure ($3): $1.

    You may discard a Treasure from your hand to gain a card costing up to $4.
    """

    def __init__(self):
        super().__init__(
            name="Anvil",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        """Resolve the optional gain when Anvil is played.

        Asks the AI which Treasure (if any) to discard from hand. If a
        Treasure is offered, discard it and gain a card costing up to $4.
        """

        player = game_state.current_player
        treasures = [card for card in player.hand if game_state.is_treasure(card)]
        if not treasures:
            return

        from ..gain_decisions import gain_menu, gain_selected, resolve_gain

        gainable = gain_menu(game_state, player, CardCost(coins=4))
        if not gainable:
            return
        pair = player.ai.choose_anvil_option(
            game_state, player, list(treasures), gainable
        )
        if not isinstance(pair, tuple) or len(pair) != 2:
            return
        choice, target = pair
        target = resolve_gain(target, gainable)
        if choice not in treasures or target is None:
            return
        player.hand.remove(choice)
        game_state.discard_card(player, choice)
        # Discard reactions may empty a pile or change its cost.
        target = resolve_gain(target, gain_menu(game_state, player, CardCost(coins=4)))
        if target is None:
            from ..gain_decisions import choose_free_gain
            target = choose_free_gain(game_state, player,
                gain_menu(game_state, player, CardCost(coins=4)), "Anvil", choice)
        gain_selected(game_state, player, target)
