from ..base_card import Card, CardCost, CardStats, CardType


class Monkey(Card):
    """Action-Duration ($3): Until your next turn, when the player to your right
    gains a card, +1 Card. At the start of your next turn, +1 Card.
    """

    def __init__(self):
        super().__init__(
            name="Monkey",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 1)
        self.duration_persistent = False

    def on_opponent_gain(self, game_state, owner, gainer, gained_card):
        """Trigger +1 Card when the player to the owner's right gains a card.

        Only active while Monkey is in the owner's duration zone (i.e. between
        the owner's turns). The on_duration callback removes it from duration.
        """
        if self not in owner.duration:
            return

        owner_idx = game_state.players.index(owner)
        right_idx = (owner_idx + 1) % len(game_state.players)
        if game_state.players[right_idx] is gainer:
            game_state.draw_cards(owner, 1)
