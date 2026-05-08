"""Herbalist - Action from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class Herbalist(Card):
    """Action ($2): +1 Buy, +$1.

    When you discard this from play, you may put one of your Treasures from
    play onto your deck.
    """

    def __init__(self):
        super().__init__(
            name="Herbalist",
            cost=CardCost(coins=2),
            stats=CardStats(buys=1, coins=1),
            types=[CardType.ACTION],
        )

    def on_discard_from_play(self, game_state, player):
        treasures = [c for c in player.in_play if c.is_treasure]
        if not treasures:
            return
        choice = player.ai.choose_treasure_to_topdeck_with_herbalist(
            game_state, player, list(treasures)
        )
        if choice is None or choice not in player.in_play:
            return
        if not choice.is_treasure:
            return
        player.in_play.remove(choice)
        player.deck.append(choice)
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"topdecks {choice.name} via Herbalist",
                {"topdecked": choice.name},
            )
        )
