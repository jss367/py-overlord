"""Counterfeit — $5 Treasure that plays another Treasure twice and trashes it."""

from ..base_card import Card, CardCost, CardStats, CardType


class Counterfeit(Card):
    """+$1 +1 Buy. When you play this, you may play a Treasure from your hand
    twice; if you do, trash it.
    """

    def __init__(self):
        super().__init__(
            name="Counterfeit",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        treasures = [c for c in player.hand if c.is_treasure]
        choice = player.ai.should_replay_treasure_with_counterfeit(
            game_state, player, treasures
        )
        if not choice or choice not in player.hand:
            return

        # Move into in-play and play twice
        player.hand.remove(choice)
        player.in_play.append(choice)
        choice.on_play(game_state)
        game_state.fire_ally_play_hooks(player, choice)
        choice.on_play(game_state)
        game_state.fire_ally_play_hooks(player, choice)

        # Trash the played treasure
        if choice in player.in_play:
            player.in_play.remove(choice)
        game_state.trash_card(player, choice)
