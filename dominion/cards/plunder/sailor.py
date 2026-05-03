"""Sailor from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Sailor(Card):
    """$4 Action-Duration.

    +1 Action. Once this turn, when you gain a Duration card, you may play
    it. At the start of your next turn, +$2 and you may trash a card from
    your hand.
    """

    def __init__(self):
        super().__init__(
            name="Sailor",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True
        self._owner = None
        self._gain_play_armed = False

    def play_effect(self, game_state):
        player = game_state.current_player
        self._owner = player
        self._gain_play_armed = True
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 2

        if player.hand:
            choice = player.ai.choose_card_to_trash(
                game_state, list(player.hand) + [None]
            )
            if choice is not None and choice in player.hand:
                player.hand.remove(choice)
                game_state.trash_card(player, choice)

        self.duration_persistent = False

    def on_card_gained(self, game_state, owner, gainer, gained_card):
        if not self._gain_play_armed:
            return
        if gainer is not self._owner or owner is not self._owner:
            return
        if not gained_card.is_duration:
            return
        if not gainer.ai.sailor_should_play_duration_on_gain(
            game_state, gainer, gained_card
        ):
            return

        # Move the gained card from wherever it landed to in_play and play it.
        if gained_card in gainer.discard:
            gainer.discard.remove(gained_card)
        elif gained_card in gainer.deck:
            gainer.deck.remove(gained_card)
        elif gained_card in gainer.hand:
            gainer.hand.remove(gained_card)
        else:
            return

        self._gain_play_armed = False
        gainer.in_play.append(gained_card)
        gained_card.on_play(game_state)

    def on_discard_from_play(self, game_state, player):
        self._gain_play_armed = False
        self._owner = None
