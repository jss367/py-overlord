from ..base_card import Card, CardCost, CardStats, CardType


class Dismantle(Card):
    def __init__(self):
        super().__init__(
            name="Dismantle",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if not choice or choice not in player.hand:
            return

        player.hand.remove(choice)
        game_state.trash_card(player, choice)

        if choice.cost.coins < 1:
            return

        from ..registry import get_card

        cheaper = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins < choice.cost.coins
        ]
        if cheaper:
            options = [get_card(name) for name in cheaper]
            gain_choice = player.ai.choose_card_to_gain_with_dismantle(
                game_state, player, choice, options + [None]
            )
            if gain_choice and gain_choice.name in game_state.supply and game_state.supply[gain_choice.name] > 0:
                game_state.supply[gain_choice.name] -= 1
                game_state.gain_card(player, get_card(gain_choice.name))

        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))
