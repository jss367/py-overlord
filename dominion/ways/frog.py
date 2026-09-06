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
        # Likewise an off-turn Reaction play (Sheepdog, Trail...) puts the card
        # in the reactor's in_play, but it is not discarded from play *this*
        # turn -- Frog's "this turn" ends with the turn player's turn -- so a
        # marker would survive to the reactor's own cleanup and topdeck the
        # card then. Only mark cards the turn player is playing.
        #
        # The marker names the owner and the turn it was set in (the player's
        # own turn counter, which also advances on Outpost/Journey extra
        # turns), and cleanup only honours a marker from the current player's
        # current turn. A card that leaves play after being marked -- Throne
        # Room's second play picks Turtle, Horse or Butterfly; Procession
        # trashes it -- keeps the attribute, but when it comes back on a later
        # turn the expired Frog no longer topdecks it. The owner is part of the
        # key because turn counters are only unique per player: a trashed
        # marked card that Lurker + Innovation gains and plays for an opponent
        # with the same ``turns_taken`` must not topdeck at their cleanup.
        if card in player.in_play and game_state.turn_player is player:
            card._frog_topdeck = (id(player), player.turns_taken)
