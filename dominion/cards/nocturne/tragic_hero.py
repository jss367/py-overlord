from ..base_card import Card, CardCost, CardStats, CardType


class TragicHero(Card):
    """Nocturne Tragic Hero implementation."""

    def __init__(self):
        super().__init__(
            name="Tragic Hero",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if len(player.hand) < 8:
            return

        if self in player.in_play:
            player.in_play.remove(self)
        game_state.trash_card(player, self)

        for treasure_name in ("Gold", "Silver", "Copper"):
            if game_state.supply.get(treasure_name, 0) > 0:
                game_state.supply[treasure_name] -= 1
                treasure = get_card(treasure_name)
                player.hand.append(treasure)
                treasure.on_gain(game_state, player)
                break
