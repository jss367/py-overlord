"""Rules-faithful implementation of Count."""

from ..base_card import Card, CardCost, CardStats, CardType


class Count(Card):
    FIRST_CHOICES = ("discard", "topdeck", "gain_copper")
    SECOND_CHOICES = ("coins", "trash_hand", "gain_duchy")

    def __init__(self):
        super().__init__(
            name="Count",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        first = player.ai.choose_count_first_option(
            game_state, player, list(self.FIRST_CHOICES)
        )
        if first not in self.FIRST_CHOICES:
            first = "discard"
        self._resolve_first_choice(game_state, player, first)

        second = player.ai.choose_count_second_option(
            game_state, player, list(self.SECOND_CHOICES)
        )
        if second not in self.SECOND_CHOICES:
            second = "coins"
        self._resolve_second_choice(game_state, player, second)

    def _resolve_first_choice(self, game_state, player, choice: str):
        from ..registry import get_card

        if choice == "discard":
            if not player.hand:
                return

            desired = 2
            selected = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), desired
            )
            pool = list(player.hand)
            while len(selected) < desired and pool:
                candidate = min(pool, key=lambda c: (c.cost.coins, c.name))
                if candidate not in selected:
                    selected.append(candidate)
                pool.remove(candidate)

            for card in selected[:desired]:
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)
            return

        if choice == "topdeck":
            if not player.hand:
                return

            card = player.ai.choose_card_to_topdeck(game_state, player, list(player.hand))
            if card is None:
                card = max(player.hand, key=lambda c: (c.cost.coins, c.stats.cards, c.name))
            if card in player.hand:
                player.hand.remove(card)
                player.deck.append(card)
            return

        if choice == "gain_copper" and game_state.supply.get("Copper", 0) > 0:
            game_state.supply["Copper"] -= 1
            copper = get_card("Copper")
            game_state.gain_card(player, copper)

    def _resolve_second_choice(self, game_state, player, choice: str):
        from ..registry import get_card

        if choice == "coins":
            player.coins += 3
            return

        if choice == "trash_hand":
            while player.hand:
                card = player.hand.pop()
                game_state.trash_card(player, card)
            return

        if choice == "gain_duchy" and game_state.supply.get("Duchy", 0) > 0:
            game_state.supply["Duchy"] -= 1
            duchy = get_card("Duchy")
            game_state.gain_card(player, duchy)
