"""Squire — $2 Action that flexes between actions/buys/silver and gains an Attack on trash."""

from ..base_card import Card, CardCost, CardStats, CardType


class Squire(Card):
    """+$1. Choose one: +2 Actions; +2 Buys; or gain a Silver.

    When you trash this, gain an Attack card.
    """

    def __init__(self):
        super().__init__(
            name="Squire",
            cost=CardCost(coins=2),
            stats=CardStats(coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        options = ["actions", "buys", "silver"]
        choice = player.ai.choose_squire_option(game_state, player, options)
        if choice not in options:
            choice = "actions"

        if choice == "actions":
            player.actions += 2
        elif choice == "buys":
            player.buys += 2
        elif choice == "silver":
            if game_state.supply.get("Silver", 0) > 0:
                game_state.supply["Silver"] -= 1
                game_state.gain_card(player, get_card("Silver"))

    def on_trash(self, game_state, player):
        from ..registry import get_card, get_all_card_names

        candidates: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                c = get_card(name)
            except ValueError:
                continue
            if c.is_attack and c.may_be_bought(game_state):
                candidates.append(c)

        if not candidates:
            return

        choice = player.ai.choose_attack_to_gain_from_squire(
            game_state, player, candidates
        )
        if choice and game_state.supply.get(choice.name, 0) > 0:
            game_state.supply[choice.name] -= 1
            game_state.gain_card(player, get_card(choice.name))
