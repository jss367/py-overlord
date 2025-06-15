from ..base_card import Card, CardCost, CardStats, CardType


class Forge(Card):
    def __init__(self):
        super().__init__(
            name="Forge",
            cost=CardCost(coins=7),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        trashed = []
        while player.hand:
            choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
            if not choice:
                break
            player.hand.remove(choice)
            game_state.trash_card(player, choice)
            trashed.append(choice)

        total = sum(c.cost.coins for c in trashed)
        if total == 0:
            return

        gains = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins == total
        ]
        if not gains:
            return

        gain_card = player.ai.choose_buy(game_state, [get_card(n) for n in gains] + [None])
        if gain_card is None:
            gain_card = get_card(gains[0])

        game_state.supply[gain_card.name] -= 1
        player.discard.append(gain_card)
        gain_card.on_gain(game_state, player)
