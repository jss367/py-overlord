"""Counterfeit — $5 Treasure that plays another Treasure twice and trashes it."""

from ..base_card import Card, CardCost, CardStats, CardType


class Counterfeit(Card):
    """+$1 +1 Buy. You may play a non-Duration Treasure from your hand
    twice; if you do, trash it (2022 wording).
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

        treasures = [c for c in player.hand
                     if game_state.is_treasure(c) and not c.is_duration]
        if not treasures:
            return
        choice = player.ai.should_replay_treasure_with_counterfeit(
            game_state, player, treasures
        )
        if choice not in treasures:
            return

        # Move into in-play and play twice
        if not game_state.move_card_from_hand_to_play(player, choice):
            return
        for _ in range(2):
            game_state.play_treasure_indirectly(player, choice)

        # Trash the played treasure
        if choice in player.in_play:
            player.in_play.remove(choice)
            game_state.trash_card(player, choice)
