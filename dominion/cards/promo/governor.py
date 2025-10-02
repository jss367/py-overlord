from ..base_card import Card, CardCost, CardStats, CardType

class Governor(Card):
    """Flexible payload that benefits everyone."""

    def __init__(self):
        super().__init__(
            name="Governor",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        options = ["cards", "gold", "upgrade"]
        choice = player.ai.choose_governor_option(game_state, player, options)

        if choice == "cards":
            self._do_cards_option(game_state, player)
        elif choice == "gold":
            self._do_gold_option(game_state, player)
        else:
            handled = self._do_upgrade_option(game_state, player)
            if not handled:
                self._do_cards_option(game_state, player)

    def _do_cards_option(self, game_state, player):
        game_state.draw_cards(player, 3)
        for other in game_state.players:
            if other is player:
                continue
            game_state.draw_cards(other, 1)

    def _do_gold_option(self, game_state, player):
        from ..registry import get_card

        gold = get_card("Gold")
        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, gold)
        for other in game_state.players:
            if other is player:
                continue
            if game_state.supply.get("Silver", 0) > 0:
                game_state.supply["Silver"] -= 1
                game_state.gain_card(other, get_card("Silver"))

    def _do_upgrade_option(self, game_state, player):
        if not player.hand:
            return False
        to_trash = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if not to_trash or to_trash not in player.hand:
            return False
        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)

        from ..registry import get_card

        max_cost = to_trash.cost.coins + 2
        affordable = [
            get_card(name)
            for name, count in game_state.supply.items()
            if count > 0
            and get_card(name).cost.coins <= max_cost
            and get_card(name).cost.potions <= to_trash.cost.potions
        ]
        if affordable:
            gain = player.ai.choose_buy(game_state, affordable + [None])
            if gain is None or gain.name not in game_state.supply or game_state.supply[gain.name] <= 0:
                gain = affordable[0]
            game_state.supply[gain.name] -= 1
            game_state.gain_card(player, get_card(gain.name))

        for other in game_state.players:
            if other is player or not other.hand:
                continue
            other_trash = other.ai.choose_card_to_trash(game_state, list(other.hand))
            if not other_trash or other_trash not in other.hand:
                continue
            other.hand.remove(other_trash)
            game_state.trash_card(other, other_trash)
            max_other_cost = other_trash.cost.coins + 2
            gains = [
                get_card(name)
                for name, count in game_state.supply.items()
                if count > 0
                and get_card(name).cost.coins <= max_other_cost
                and get_card(name).cost.potions <= other_trash.cost.potions
            ]
            if gains:
                selection = other.ai.choose_buy(game_state, gains + [None])
                if selection is None or selection.name not in game_state.supply or game_state.supply[selection.name] <= 0:
                    selection = gains[0]
                game_state.supply[selection.name] -= 1
                game_state.gain_card(other, get_card(selection.name))
        return True
