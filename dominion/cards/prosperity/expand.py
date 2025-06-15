from ..base_card import Card, CardCost, CardStats, CardType


class Expand(Card):
    def __init__(self):
        super().__init__(
            name="Expand",
            cost=CardCost(coins=7),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return

        card_to_trash = player.ai.choose_card_to_trash(game_state, player.hand)
        if card_to_trash is None:
            card_to_trash = player.hand[0]

        player.hand.remove(card_to_trash)
        game_state.trash_card(player, card_to_trash)

        max_cost = card_to_trash.cost.coins + 3
        gains = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins <= max_cost
        ]
        if not gains:
            return

        gain_card = player.ai.choose_buy(game_state, [get_card(n) for n in gains])
        if gain_card is None:
            gain_card = get_card(gains[0])

        game_state.supply[gain_card.name] -= 1
        player.discard.append(gain_card)
        gain_card.on_gain(game_state, player)
