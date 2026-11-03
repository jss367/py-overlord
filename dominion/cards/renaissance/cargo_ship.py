from ..base_card import Card, CardCost, CardStats, CardType


class CargoShip(Card):
    def __init__(self):
        super().__init__(
            name="Cargo Ship",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self._gain_plays = 0
        self._gain_state = None
        self._gain_turn = None
        self.set_aside = []

    @property
    def waiting_for_gain(self):
        return self._gain_plays > 0 and (
            self._gain_state is None
            or (
                self._gain_turn[0] == self._gain_state.turn_number
                and self._gain_turn[1] == self._gain_state.turn_player.turns_taken
                and self._gain_turn[2] is self._gain_state.turn_player
            )
        )

    def play_effect(self, game_state):
        # Each play creates its own optional rest-of-turn instruction. This
        # matters when multiple Estates play the same physical set-aside card.
        self._gain_plays = (self._gain_plays if self.waiting_for_gain else 0) + 1
        self._gain_state = game_state
        self._gain_turn = (game_state.turn_number, game_state.turn_player.turns_taken, game_state.turn_player)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.hand.extend(self.set_aside)
        self.set_aside = []
        self.duration_persistent = False

    def on_cargo_ship_gain(self, game_state, player, gained_card):
        if not self.waiting_for_gain:
            return False
        if not player.ai.should_set_aside_cargo_ship(game_state, player, gained_card):
            return False
        if not game_state.gain_is_movable(player, gained_card):
            return False
        origin = game_state.gain_destination(gained_card)
        origin.remove(gained_card)
        self._gain_plays -= 1
        self.set_aside.append(gained_card)
        player.duration.append(self)
        self.duration_persistent = True
        return True
