"""Sheepdog - Action-Reaction from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Sheepdog(Card):
    """+2 Cards. When you gain a card you may play this from your hand."""

    def __init__(self):
        super().__init__(
            name="Sheepdog",
            cost=CardCost(coins=3),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def react_to_own_gain(self, game_state, player, gained_card) -> bool:
        """Hook used by gain handler. Owner may play this from hand."""
        if self not in player.hand:
            return False
        if not player.ai.should_play_sheepdog(game_state, player, gained_card):
            return False

        player.hand.remove(self)
        player.in_play.append(self)
        # Gains can happen on other players' turns (e.g. via an opponent's
        # Black Cat Curse), so resolve Sheepdog's effects from the perspective
        # of its owner rather than ``game_state.current_player``.
        original_index = game_state.current_player_index
        try:
            game_state.current_player_index = game_state.players.index(player)
        except ValueError:
            # Owner not registered as a player (defensive); fall back to the
            # current play context.
            self.on_play(game_state)
            game_state.fire_ally_play_hooks(player, self)
            return True
        try:
            self.on_play(game_state)
            game_state.fire_ally_play_hooks(player, self)
        finally:
            game_state.current_player_index = original_index
        return True
