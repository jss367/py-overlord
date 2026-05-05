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
            # Dark Ages: the "Knights" placeholder isn't directly buyable —
            # the actual gainable card is the top Knight in pile_order. Use
            # that top card so Squire can gain a Knight when Knights is the
            # only Attack pile.
            if name == "Knights" and "Knights" in game_state.pile_order:
                pile = game_state.pile_order.get("Knights") or []
                if not pile:
                    continue
                top_name = pile[-1]
                try:
                    c = get_card(top_name)
                except ValueError:
                    continue
                if c.is_attack:
                    candidates.append(c)
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
        if not choice:
            return

        # Resolve the supply pile (Knights → "Knights"; otherwise card name).
        pile_name = "Knights" if choice.is_knight and "Knights" in game_state.pile_order else choice.name
        if game_state.supply.get(pile_name, 0) <= 0:
            return
        if pile_name == "Knights":
            order = game_state.pile_order.get("Knights") or []
            if not order:
                return
            top_name = order.pop()
            game_state.supply["Knights"] -= 1
            game_state.gain_card(player, get_card(top_name))
        else:
            game_state.supply[pile_name] -= 1
            game_state.gain_card(player, get_card(choice.name))
