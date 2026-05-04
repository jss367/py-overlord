"""Sleigh - Action-Reaction from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Sleigh(Card):
    """Gain 2 Horses. When you gain a card, you may discard this from hand
    to put that card into your hand or onto your deck.
    """

    def __init__(self):
        super().__init__(
            name="Sleigh",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        for _ in range(2):
            if game_state.supply.get("Horse", 0) <= 0:
                break
            game_state.supply["Horse"] -= 1
            game_state.gain_card(player, get_card("Horse"))

    def react_to_own_gain(self, game_state, player, gained_card) -> str | None:
        """Hook used by gain handler. Returns 'hand', 'deck', or None."""
        if self not in player.hand:
            return None
        decision = player.ai.choose_sleigh_reaction(game_state, player, gained_card)
        if decision not in {"hand", "deck"}:
            return None
        # Discard the Sleigh
        player.hand.remove(self)
        game_state.discard_card(player, self)
        return decision
