import random

from ..base_card import Card, CardCost, CardStats, CardType


class Pickaxe(Card):
    def __init__(self):
        super().__init__(
            name="Pickaxe",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if not choice or choice not in player.hand:
            choice = player.hand[0]
        trashed_cost = game_state.get_card_cost(player, choice)
        player.hand.remove(choice)
        game_state.trash_card(player, choice)
        if trashed_cost >= 3:
            self._gain_loot(game_state, player)

    def _gain_loot(self, game_state, player):
        from ..registry import get_card
        from ..plunder.loot_cards import LOOT_CARD_NAMES

        loot_name = random.choice(LOOT_CARD_NAMES)
        loot = get_card(loot_name)
        gained = game_state.gain_card(player, loot)
        if gained in player.discard:
            player.discard.remove(gained)
            player.hand.append(gained)
