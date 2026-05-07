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
        # Move this Royal Carriage off the mat first so the replay's own
        # ``action_played`` trigger doesn't re-enter this same instance.
        game_state.call_from_tavern(player, self)
        # Replay the action card.
        action_card.on_play(game_state)
        # The replay is itself a play of the action: other Reserves on the mat
        # (another Royal Carriage, Coin of the Realm) get to react.
        game_state._call_tavern_triggers(player, "action_played", action_card)
        return True
