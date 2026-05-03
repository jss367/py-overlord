from ..base_card import Card, CardCost, CardStats, CardType


class Corsair(Card):
    """Action-Duration-Attack ($5): +$2. At the start of your next turn, +1 Card.
    Until then, the first time each other player plays a Silver or a Gold on each
    of their turns, they trash it.
    """

    def __init__(self):
        super().__init__(
            name="Corsair",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self.duration_persistent = True
        self.active = False

    def play_effect(self, game_state):
        player = game_state.current_player
        self.active = True
        player.duration.append(self)
        # Owner attribution lets the on_treasure_played hook find the Corsair.
        self._owner = player

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 1)
        self.active = False
        self.duration_persistent = False
        self._owner = None

    def react_to_treasure_played(self, game_state, treasure_player, treasure_card):
        """Trash the first Silver/Gold each opponent plays each turn while active.

        Called from the treasure-play path. Returns True if the treasure was
        trashed, False otherwise.
        """
        if not self.active:
            return False
        owner = getattr(self, "_owner", None)
        if owner is None or treasure_player is owner:
            return False
        if treasure_card.name not in {"Silver", "Gold"}:
            return False

        if treasure_player.corsair_trashed_this_turn:
            return False

        treasure_player.corsair_trashed_this_turn = True
        # Remove from in_play and trash it.
        if treasure_card in treasure_player.in_play:
            treasure_player.in_play.remove(treasure_card)
        game_state.trash_card(treasure_player, treasure_card)
        return True
