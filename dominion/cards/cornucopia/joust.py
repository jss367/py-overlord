from ..base_card import Card, CardCost, CardStats, CardType


REWARD_CARD_NAMES = [
    "Coronet",
    "Demesne",
    "Housecarl",
    "Huge Turnip",
    "Renown",
]


class Joust(Card):
    def __init__(self):
        super().__init__(
            name="Joust",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1, coins=1),
            types=[CardType.ACTION],
        )
        self.province_set_aside = None

    def get_additional_piles(self) -> dict[str, int]:
        return {name: 5 for name in REWARD_CARD_NAMES}

    def play_effect(self, game_state):
        player = game_state.current_player
        province = None
        for card in player.hand:
            if card.name == "Province":
                province = card
                break
        if not province:
            return
        if not player.ai.should_joust_province(game_state, player):
            return
        player.hand.remove(province)
        self.province_set_aside = province
        from ..registry import get_card
        available_rewards = []
        for name in REWARD_CARD_NAMES:
            if game_state.supply.get(name, 0) > 0:
                available_rewards.append(get_card(name))
        if not available_rewards:
            return
        choice = player.ai.choose_buy(game_state, available_rewards)
        if not choice or choice not in available_rewards:
            choice = available_rewards[0]
        game_state.supply[choice.name] -= 1
        gained = game_state.gain_card(player, choice)
        if gained in player.discard:
            player.discard.remove(gained)
            player.hand.append(gained)

    def on_cleanup_return_province(self, player):
        if self.province_set_aside:
            player.hand.append(self.province_set_aside)
            self.province_set_aside = None
