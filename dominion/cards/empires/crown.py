from ..base_card import Card, CardCost, CardStats, CardType


class Crown(Card):
    """Lets you double-play an Action (action phase) or Treasure (treasure phase)."""

    def __init__(self):
        super().__init__(
            name="Crown",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, coins=1),
            types=[CardType.ACTION, CardType.TREASURE],
        )

    def play_effect(self, game_state):
        """Play another card from hand twice based on the current phase."""

        player = game_state.current_player

        if game_state.phase == "action":
            targets = [card for card in player.hand if card.is_action]
            if not targets:
                return

            choice = player.ai.choose_action(game_state, targets + [None])
            if choice is None:
                choice = targets[0]

            player.hand.remove(choice)
            player.in_play.append(choice)

            for _ in range(2):
                choice.on_play(game_state)
        else:
            treasures = [card for card in player.hand if card.is_treasure]
            if not treasures:
                return

            choice = player.ai.choose_treasure(game_state, treasures + [None])
            if choice is None:
                choice = treasures[0]

            player.hand.remove(choice)
            player.in_play.append(choice)

            for _ in range(2):
                choice.on_play(game_state)
