from ..base_card import Card, CardCost, CardStats, CardType


class IllGottenGains(Card):
    def __init__(self):
        super().__init__(
            name="Ill-Gotten Gains",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        for other in game_state.players:
            if other is player:
                continue
            game_state.give_curse_to_player(other)

    def play_effect(self, game_state):
        player = game_state.current_player

        if game_state.supply.get("Copper", 0) <= 0:
            return

        if not self._should_gain_copper(game_state, player):
            return

        from ..registry import get_card

        copper = get_card("Copper")
        game_state.supply["Copper"] -= 1
        player.hand.append(copper)
        copper.on_gain(game_state, player)

    @staticmethod
    def _should_gain_copper(game_state, player) -> bool:
        """Decide whether gaining a Copper now meaningfully improves buys."""

        current_coins = player.coins
        coins_with_copper = current_coins + 1

        def best_affordable_value(available_coins: int) -> int:
            best = -1

            from ..registry import get_card

            for card_name, count in game_state.supply.items():
                if count <= 0:
                    continue
                card = get_card(card_name)
                if card_name in player.banned_buys:
                    continue

                cost = game_state.get_card_cost(player, card)
                if cost > available_coins or card.cost.potions > player.potions:
                    continue
                if not card.may_be_bought(game_state):
                    continue
                best = max(best, cost)

            for event in game_state.events:
                if event.cost.coins > available_coins:
                    continue
                if event.cost.potions > player.potions:
                    continue
                if not event.may_be_bought(game_state, player):
                    continue
                best = max(best, event.cost.coins)

            for project in game_state.projects:
                if project in player.projects:
                    continue
                if project.cost.coins > available_coins:
                    continue
                if project.cost.potions > player.potions:
                    continue
                if not project.may_be_bought(game_state, player):
                    continue
                best = max(best, project.cost.coins)

            return best

        return best_affordable_value(coins_with_copper) > best_affordable_value(current_coins)
