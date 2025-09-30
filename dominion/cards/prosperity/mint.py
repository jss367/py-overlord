from ..base_card import Card, CardCost, CardStats, CardType


class Mint(Card):
    def __init__(self):
        super().__init__(
            name="Mint",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        treasures = [c for c in player.hand if c.is_treasure]
        if not treasures:
            return

        chosen = player.ai.choose_treasure(game_state, treasures)
        if chosen is None:
            chosen = treasures[0]

        if game_state.supply.get(chosen.name, 0) > 0:
            game_state.supply[chosen.name] -= 1
            gained = get_card(chosen.name)
            game_state.gain_card(player, gained)

    def on_buy(self, game_state):
        player = game_state.current_player
        treasures = [c for c in list(player.in_play) if c.is_treasure]
        for treasure in treasures:
            player.in_play.remove(treasure)
            game_state.trash_card(player, treasure)
