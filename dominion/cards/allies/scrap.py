"""Implementation of the Scrap card from Allies.

Trash a card from your hand. Choose one per $1 it costs:
+1 Card; +1 Action; +1 Buy; +$1; gain a Silver; gain a card costing
exactly $1. Options may be chosen more than once.
"""

from ..base_card import Card, CardCost, CardStats, CardType


SCRAP_OPTIONS = ("card", "action", "buy", "coin", "silver", "one_cost")


class Scrap(Card):
    def __init__(self):
        super().__init__(
            name="Scrap",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return

        to_trash = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if to_trash is None or to_trash not in player.hand:
            return

        cost = to_trash.cost.coins
        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)

        if cost <= 0:
            return

        picks = self._select_picks(game_state, player, cost)

        for pick in picks[:cost]:
            if pick == "card":
                game_state.draw_cards(player, 1)
            elif pick == "action":
                if not player.ignore_action_bonuses:
                    player.actions += 1
            elif pick == "buy":
                player.buys += 1
            elif pick == "coin":
                player.coins += 1
            elif pick == "silver":
                if game_state.supply.get("Silver", 0) > 0:
                    game_state.supply["Silver"] -= 1
                    game_state.gain_card(player, get_card("Silver"))
            elif pick == "one_cost":
                self._gain_card_costing_one(game_state, player)

    def _select_picks(self, game_state, player, count: int) -> list[str]:
        chooser = getattr(player.ai, "choose_scrap_options", None)
        if chooser is not None:
            picks = chooser(game_state, player, count, list(SCRAP_OPTIONS))
            if picks:
                return list(picks)
        return self._default_picks(player, count)

    def _default_picks(self, player, count: int) -> list[str]:
        picks: list[str] = []
        # Cantrip-flavored default: alternate +Card and +$1, with one +Action
        # if the player has none, since +Action is rarely needed twice.
        needs_action = player.actions == 0
        for i in range(count):
            if needs_action and i == 0:
                picks.append("action")
            elif i % 2 == 0:
                picks.append("card")
            else:
                picks.append("coin")
        return picks

    def _gain_card_costing_one(self, game_state, player) -> None:
        from ..registry import get_card

        candidates = []
        for name, supply_count in game_state.supply.items():
            if supply_count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.potions > 0 or card.cost.debt > 0:
                continue
            if card.cost.coins != 1:
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)
        if not candidates:
            return
        chosen = player.ai.choose_buy(game_state, candidates + [None])
        if chosen is None:
            return
        if game_state.supply.get(chosen.name, 0) <= 0:
            return
        game_state.supply[chosen.name] -= 1
        game_state.gain_card(player, chosen)
