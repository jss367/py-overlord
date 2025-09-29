from ..base_card import Card, CardCost, CardStats, CardType


class Develop(Card):
    def __init__(self):
        super().__init__(
            name="Develop",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.hand:
            return

        to_trash = player.ai.choose_card_to_trash(game_state, player.hand)
        if not to_trash:
            to_trash = min(player.hand, key=lambda card: (card.cost.coins, card.name))

        if to_trash not in player.hand:
            return

        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)

        from ..registry import get_card

        for delta in (-1, 1):
            target_cost = to_trash.cost.coins + delta
            if target_cost < 0:
                continue

            options = [
                get_card(name)
                for name, count in game_state.supply.items()
                if count > 0 and get_card(name).cost.coins == target_cost
            ]
            if not options:
                continue

            choice = player.ai.choose_buy(game_state, options + [None])
            if not choice:
                choice = max(options, key=lambda card: (card.cost.coins, card.name))

            if game_state.supply.get(choice.name, 0) <= 0:
                continue

            game_state.supply[choice.name] -= 1
            game_state.gain_card(player, choice, to_deck=True)
