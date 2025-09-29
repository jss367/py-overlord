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

        to_trash = self._choose_trash(treasures)
        if not to_trash:
            return

        if to_trash not in player.hand:
            return

        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)

        if self._prefer_draw_option(player):
            game_state.draw_cards(player, 2)
            player.actions += 1
        else:
            player.coins += 2
            player.buys += 1

    @staticmethod
    def _choose_trash(treasures):
        for name in ["Copper", "Silver", "Gold"]:
            for card in treasures:
                if card.name == name:
                    return card
        return treasures[0] if treasures else None

    @staticmethod
    def _prefer_draw_option(player) -> bool:
        remaining_actions = sum(1 for card in player.hand if card.is_action)
        if remaining_actions:
            return True
        if player.actions <= 0:
            return True
        return player.coins < 3
