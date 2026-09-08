from .base_ally import Ally


class LeagueOfShopkeepers(Ally):
    def __init__(self):
        super().__init__("League of Shopkeepers")

    def on_play_card(self, game_state, player, card):
        if not card.is_liaison:
            return
        if player.favors >= 5:
            player.coins += 1
        if player.favors >= 10:
            player.buys += 1
            if not player.ignore_action_bonuses:
                player.actions += 1
