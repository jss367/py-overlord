"""Way of the Frog — +1 Action. Topdeck this card on Cleanup."""

from .base_way import Way


class WayOfTheFrog(Way):
    def __init__(self):
        super().__init__("Way of the Frog")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        player.actions += 1
        # "When you discard this from play this turn, put it onto your deck."
        # That cannot apply to a card that is not in play (Necromancer's
        # trashed card, Riverboat's set-aside card, Captain's Supply proxy),
        # and cleanup only clears the marker while iterating cards in play,
        # so a marker set on such a card would persist and topdeck that
        # instance on a later turn. Only mark cards that are actually in play.
        if card in player.in_play:
            card._frog_topdeck = True
