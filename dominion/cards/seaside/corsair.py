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
        # Identities (object id) of opponents who weren't immune at play time.
        self._affected_player_ids: set[int] = set()

    def play_effect(self, game_state):
        player = game_state.current_player
        self.active = True
        player.duration.append(self)
        self._owner = player
        self._affected_player_ids = set()

        # Resolve the attack at play time so Moat / Lighthouse / Shield can
        # exempt opponents from the deferred-trash effect for this Corsair.
        def attack_target(target):
            self._affected_player_ids.add(id(target))

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 1)
        self.active = False
        self.duration_persistent = False
        self._owner = None
        self._affected_player_ids = set()

    def react_to_treasure_played(self, game_state, treasure_player, treasure_card):
        """Trash the first Silver/Gold each affected opponent plays each turn.

        Returns True if the treasure was trashed, False otherwise.
        """
        if not self.active:
            return False
        owner = getattr(self, "_owner", None)
        if owner is None or treasure_player is owner:
            return False
        if treasure_card.name not in {"Silver", "Gold"}:
            return False
        if id(treasure_player) not in self._affected_player_ids:
            return False
        if treasure_player.corsair_trashed_this_turn:
            return False

        treasure_player.corsair_trashed_this_turn = True
        if treasure_card in treasure_player.in_play:
            treasure_player.in_play.remove(treasure_card)
        game_state.trash_card(treasure_player, treasure_card)
        return True
