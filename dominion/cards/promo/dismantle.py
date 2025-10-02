from ..base_card import Card, CardCost, CardStats, CardType

class Dismantle(Card):
    """Trashes a card for a Gold to hand and a cheaper gain."""

    def __init__(self):
        super().__init__(
            name="Dismantle",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        to_trash = player.ai.choose_card_to_trash(game_state, list(player.hand) + [None])
        if not to_trash or to_trash not in player.hand:
            return
        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)

        if game_state.supply.get("Gold", 0) > 0:
            from ..registry import get_card

            game_state.supply["Gold"] -= 1
            gained_gold = game_state.gain_card(player, get_card("Gold"))
            if gained_gold in player.discard:
                player.discard.remove(gained_gold)
                player.hand.append(gained_gold)

        from ..registry import get_card

        cheaper = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins < to_trash.cost.coins
        ]
        if not cheaper:
            return
        choices = [get_card(name) for name in cheaper]
        gain_choice = player.ai.choose_buy(game_state, choices + [None])
        if gain_choice is None or gain_choice.name not in cheaper:
            gain_choice = choices[0]
        game_state.supply[gain_choice.name] -= 1
        game_state.gain_card(player, get_card(gain_choice.name))
