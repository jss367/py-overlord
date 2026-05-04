"""Haunted Mirror — Cemetery's Heirloom."""

from ...base_card import Card, CardCost, CardStats, CardType


class HauntedMirror(Card):
    """$1 Treasure-Heirloom.

    When you discard this from play, you may discard an Action card to gain
    a Ghost. The cleanup loop fires ``on_discard_from_play`` once per card
    in play before discarding the hand, which is the right hook for this.
    """

    def __init__(self):
        super().__init__(
            name="Haunted Mirror",
            cost=CardCost(coins=2),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE, CardType.HEIRLOOM],
        )

    def starting_supply(self, game_state) -> int:  # pragma: no cover
        return 0

    def on_discard_from_play(self, game_state, player):
        actions_in_hand = [c for c in player.hand if c.is_action]
        if not actions_in_hand:
            return
        chosen = player.ai.should_play_haunted_mirror_action_discard(
            game_state, player, actions_in_hand
        )
        if chosen is None or chosen not in player.hand:
            return
        player.hand.remove(chosen)
        game_state.discard_card(player, chosen)
        if game_state.supply.get("Ghost", 0) <= 0:
            return
        game_state.supply["Ghost"] -= 1
        from ...registry import get_card

        game_state.gain_card(player, get_card("Ghost"))
