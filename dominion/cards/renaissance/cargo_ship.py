from ..base_card import Card, CardCost, CardStats, CardType


class CargoShip(Card):
    def __init__(self):
        super().__init__(
            name="Cargo Ship",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.waiting_for_gain = False
        self.set_aside = None

    def play_effect(self, game_state):
        self.waiting_for_gain = True

    def on_duration(self, game_state):
        player = game_state.current_player
        if self.set_aside:
            player.hand.append(self.set_aside)
            self.set_aside = None
        self.duration_persistent = False

    def on_cargo_ship_gain(self, game_state, player, gained_card):
        if not self.waiting_for_gain:
            return False
        if not player.ai.should_set_aside_cargo_ship(game_state, player, gained_card):
            return False
        self.waiting_for_gain = False
        if gained_card in player.discard:
            player.discard.remove(gained_card)
        elif gained_card in player.deck:
            player.deck.remove(gained_card)
        self.set_aside = gained_card
        player.duration.append(self)
        self.duration_persistent = True
        return True
