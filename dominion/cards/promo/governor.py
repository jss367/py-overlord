from ..base_card import Card, CardCost, CardStats, CardType


class Governor(Card):
    def __init__(self):
        super().__init__(
            name="Governor",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        option = player.ai.choose_governor_option(game_state, player)
        if option == "gain":
            self._gain_option(game_state, player)
        elif option == "remodel":
            self._remodel_option(game_state, player)
        else:
            self._draw_option(game_state, player)

    def _draw_option(self, game_state, player):
        game_state.draw_cards(player, 3)
        for other in game_state.players:
            if other is player:
                continue
            game_state.draw_cards(other, 1)

    def _gain_option(self, game_state, player):
        from ..registry import get_card

        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))
        for other in game_state.players:
            if other is player:
                continue
            if game_state.supply.get("Silver", 0) <= 0:
                continue
            game_state.supply["Silver"] -= 1
            game_state.gain_card(other, get_card("Silver"))

    def _remodel_option(self, game_state, player):
        trashed = self._trash_for_governor(game_state, player, 2)
        for other in game_state.players:
            if other is player:
                continue
            self._trash_for_governor(game_state, other, 1)

    def _trash_for_governor(self, game_state, player, increase):
        if not player.hand:
            return None
        choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if not choice or choice not in player.hand:
            return None
        player.hand.remove(choice)
        game_state.trash_card(player, choice)

        target_cost = choice.cost.coins + increase
        from ..registry import get_card

        available = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins == target_cost
        ]
        if not available:
            return choice

        options = [get_card(name) for name in available]
        gain_choice = player.ai.choose_card_to_gain_for_governor(
            game_state, player, options + [None]
        )
        if not gain_choice or gain_choice.name not in game_state.supply:
            return choice
        if game_state.supply[gain_choice.name] <= 0:
            return choice
        game_state.supply[gain_choice.name] -= 1
        game_state.gain_card(player, get_card(gain_choice.name))
        return choice
