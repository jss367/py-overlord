"""Groom - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Groom(Card):
    """Gain a card costing up to $4. If it's an Action, gain a Horse; if a
    Treasure, gain a Silver; if a Victory, each other player gains a Horse.
    """

    def __init__(self):
        super().__init__(
            name="Groom",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins <= 4 and card.cost.potions == 0:
                candidates.append(card)
        if not candidates:
            return

        choice = player.ai.choose_buy(game_state, candidates + [None])
        if choice is None:
            choice = max(candidates, key=lambda c: (c.cost.coins, c.name))
        if game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        gained = game_state.gain_card(player, choice)

        if gained.is_action:
            if game_state.supply.get("Horse", 0) > 0:
                game_state.supply["Horse"] -= 1
                game_state.gain_card(player, get_card("Horse"))
        if gained.is_treasure:
            if game_state.supply.get("Silver", 0) > 0:
                game_state.supply["Silver"] -= 1
                game_state.gain_card(player, get_card("Silver"))
        if gained.is_victory:
            for other in game_state.players:
                if other is player:
                    continue
                if game_state.supply.get("Horse", 0) <= 0:
                    break
                game_state.supply["Horse"] -= 1
                game_state.gain_card(other, get_card("Horse"))
