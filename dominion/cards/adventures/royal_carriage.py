"""Royal Carriage (Adventures) — $5 Action-Reserve."""

from ..base_card import Card, CardCost, CardStats, CardType


class RoyalCarriage(Card):
    def __init__(self):
        super().__init__(
            name="Royal Carriage",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.RESERVE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.set_aside_on_tavern(player, self)

    def on_call_from_tavern(self, game_state, player, trigger, *args, **kwargs):
        if trigger != "action_played":
            return False
        if not args:
            return False
        action_card = args[0]
        # Royal Carriage requires the action to still be in play.
        if action_card not in player.in_play:
            return False
        if not player.ai.should_call_from_tavern(
            game_state, player, self, trigger, *args
        ):
            return False
        # Replay the action card.
        action_card.on_play(game_state)
        # Apply pile-token bonuses again on the replay.
        game_state._apply_pile_token_play_bonuses(player, action_card)
        if getattr(player, "champions_in_play", 0) > 0 and action_card.is_action:
            player.actions += player.champions_in_play
        game_state.call_from_tavern(player, self)
        return True
