"""Cabin Boy from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class CabinBoy(Card):
    """$3 Action-Duration: +1 Card, +1 Action.

    At start of next turn, choose: +$2; or trash this to gain a Duration card
    costing up to $5 from the supply.
    """

    def __init__(self):
        super().__init__(
            name="Cabin Boy",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        durations = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.is_duration and card.cost.coins <= 5 and card.cost.potions == 0:
                durations.append(card)

        prefer_trash = False
        if durations and hasattr(player.ai, "cabin_boy_should_trash"):
            prefer_trash = bool(player.ai.cabin_boy_should_trash(game_state, player, durations))

        if prefer_trash and durations:
            if self in player.duration:
                player.duration.remove(self)
            if self in player.in_play:
                player.in_play.remove(self)
            game_state.trash_card(player, self)

            durations.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            gain = durations[0]
            game_state.supply[gain.name] -= 1
            game_state.gain_card(player, gain)
            # Stay 'persistent' so do_duration_phase doesn't try to remove
            # this from player.duration again — we've already cleaned up.
            self.duration_persistent = True
        else:
            player.coins += 2
            self.duration_persistent = False
