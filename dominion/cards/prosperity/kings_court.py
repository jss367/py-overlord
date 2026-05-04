from ..base_card import Card, CardCost, CardStats, CardType


class KingsCourt(Card):
    """Action ($7): You may play an Action card from your hand three times.

    Like Throne Room, the chosen Action stays in play (not hand) after the
    three plays so its lingering effects (e.g. duration triggers, "while in
    play" rules, attacks blocked by Moat reactions) can resolve naturally.
    """

    def __init__(self):
        super().__init__(
            name="King's Court",
            cost=CardCost(coins=7),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        actions_in_hand = [c for c in player.hand if c.is_action]
        if not actions_in_hand:
            return

        choice = player.ai.choose_action(game_state, actions_in_hand + [None])
        if choice is None or choice not in actions_in_hand:
            choice = actions_in_hand[0]

        # Move the chosen action from hand to play before resolving so the
        # card is "in play" while its effects fire (mirrors Throne Room).
        player.hand.remove(choice)
        player.in_play.append(choice)

        for _ in range(3):
            choice.on_play(game_state)
            game_state.fire_ally_play_hooks(player, choice)
