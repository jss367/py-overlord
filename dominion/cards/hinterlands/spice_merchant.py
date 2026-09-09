"""Spice Merchant ($4): you may trash a Treasure from your hand to choose one:
+2 Cards and +1 Action; or +1 Buy and +$2."""

from ..base_card import Card, CardCost, CardStats, CardType


class SpiceMerchant(Card):
    def __init__(self):
        super().__init__(
            name="Spice Merchant",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        treasures = [card for card in player.hand if card.is_treasure]
        if not treasures:
            return

        to_trash = player.ai.choose_treasure_to_trash_for_spice_merchant(
            game_state, player, list(treasures)
        )
        if to_trash is None or to_trash not in treasures:
            return

        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)

        mode = player.ai.choose_spice_merchant_mode(game_state, player)
        draw = mode != "coins"
        from ..allies._rules import select_modes

        def resolve(draw):
            if draw:
                game_state.draw_cards(player, 2)
                player.actions += 1
            else:
                player.coins += 2
                player.buys += 1

        for draw in select_modes(game_state, player, self, [True, False], [draw]):
            resolve(draw)
