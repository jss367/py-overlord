"""Scrap - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Scrap(Card):
    """+1 Action. Trash a card from your hand. Choose one or more (different)
    per its cost: +1 Card; +1 Action; +1 Buy; +$1; gain a Silver; gain a Horse.
    """

    OPTIONS = [
        "card",
        "action",
        "buy",
        "coin",
        "silver",
        "horse",
    ]

    def __init__(self):
        super().__init__(
            name="Scrap",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return

        choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if choice is None or choice not in player.hand:
            return

        cost = choice.cost.coins
        player.hand.remove(choice)
        game_state.trash_card(player, choice)

        if cost <= 0:
            return

        n = min(cost, len(self.OPTIONS))
        # Default heuristic: always pick a useful set in stable order.
        chosen_options = player.ai.choose_scrap_options(game_state, player, n)
        if not chosen_options:
            chosen_options = self.OPTIONS[:n]

        seen = set()
        for opt in chosen_options:
            if opt in seen or opt not in self.OPTIONS:
                continue
            seen.add(opt)
            if len(seen) > n:
                break
            if opt == "card":
                game_state.draw_cards(player, 1)
            elif opt == "action":
                player.actions += 1
            elif opt == "buy":
                player.buys += 1
            elif opt == "coin":
                player.coins += 1
            elif opt == "silver":
                if game_state.supply.get("Silver", 0) > 0:
                    game_state.supply["Silver"] -= 1
                    game_state.gain_card(player, get_card("Silver"))
            elif opt == "horse":
                if game_state.supply.get("Horse", 0) > 0:
                    game_state.supply["Horse"] -= 1
                    game_state.gain_card(player, get_card("Horse"))
