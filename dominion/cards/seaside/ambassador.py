from ..base_card import Card, CardCost, CardStats, CardType


class Ambassador(Card):
    """Action-Attack ($3): Reveal a card from your hand. Return up to 2 copies of it
    from your hand to the Supply. Then each other player gains a copy of it.
    """

    def __init__(self):
        super().__init__(
            name="Ambassador",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        if not player.hand:
            return

        # Reveal is mandatory if the hand has cards. Honor the AI's choice
        # when valid; otherwise fall back to the cheapest hand card so the
        # attack still resolves (default heuristic only picks junk).
        choice = player.ai.choose_card_to_ambassador(game_state, player, list(player.hand))
        if choice is None or choice not in player.hand:
            choice = min(
                player.hand,
                key=lambda c: (c.is_action, c.is_treasure, c.cost.coins, c.name),
            )

        # Find copies in hand of the same name.
        copies = [c for c in player.hand if c.name == choice.name]
        return_count = min(2, len(copies))

        # Decide how many to return — default heuristic returns as many as possible
        # if the card is junk (Curse, Estate, Copper); otherwise just one.
        if choice.name in {"Curse", "Estate", "Copper", "Hovel", "Overgrown Estate"}:
            actual_return = return_count
        else:
            actual_return = min(1, return_count)

        # Return chosen copies to the Supply
        for _ in range(actual_return):
            for c in player.hand:
                if c.name == choice.name:
                    player.hand.remove(c)
                    break
            game_state.supply[choice.name] = game_state.supply.get(choice.name, 0) + 1

        # Each other player gains a copy
        def attack_target(target):
            if game_state.supply.get(choice.name, 0) <= 0:
                return
            game_state.supply[choice.name] -= 1
            game_state.gain_card(target, get_card(choice.name))

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
