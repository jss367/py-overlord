"""Vagrant — $2 cantrip that pulls Curse/Ruins/Shelter/Victory tops into hand."""

from ..base_card import Card, CardCost, CardStats, CardType


SHELTER_NAMES = {"Hovel", "Necropolis", "Overgrown Estate"}


class Vagrant(Card):
    """+1 Card +1 Action.

    Reveal the top card of your deck. If it is a Curse, Ruins, Shelter, or
    Victory card, put it into your hand.
    """

    def __init__(self):
        super().__init__(
            name="Vagrant",
            cost=CardCost(coins=2),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return

        top = player.deck[-1]
        is_pickup = (
            top.name == "Curse"
            or top.is_ruins
            or top.name in SHELTER_NAMES
            or top.is_victory
        )
        if is_pickup:
            player.deck.pop()
            player.hand.append(top)
