"""Coin of the Realm — Treasure-Reserve from Adventures."""

from ..base_card import Card, CardCost, CardStats, CardType


class CoinOfTheRealm(Card):
    """$2 Treasure-Reserve. $1. When you play this, put it on your Tavern mat.
    Directly after you play an Action, you may call this for +2 Actions.
    """

    def __init__(self):
        super().__init__(
            name="Coin of the Realm",
            cost=CardCost(coins=2),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE, CardType.RESERVE],
        )

    def play_effect(self, game_state):
        # The +$1 from CardStats has already been applied. Now move from
        # in_play to the Tavern mat.
        player = game_state.current_player
        game_state.set_aside_on_tavern(player, self)

    def on_call_from_tavern(self, game_state, player, trigger, *args, **kwargs):
        if trigger != "action_played":
            return False
        if not player.ai.should_call_from_tavern(
            game_state, player, self, trigger, *args
        ):
            return False
        player.actions += 2
        game_state.call_from_tavern(player, self)
        return True
