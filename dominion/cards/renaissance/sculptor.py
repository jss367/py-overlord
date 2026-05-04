"""Sculptor: Action ($5). Gain a card to your hand costing up to $4.
If it's a Treasure, +1 Villager."""

from ..base_card import Card, CardCost, CardStats, CardType


class Sculptor(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Sculptor",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        from ..registry import get_card

        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            cand = get_card(name)
            if cand.cost.potions > 0:
                continue
            if cand.cost.coins > 4:
                continue
            options.append(cand)
        if not options:
            return

        choice = player.ai.choose_buy(game_state, options + [None])
        if choice is None:
            choice = max(
                options,
                key=lambda c: (c.is_action, c.is_treasure, c.cost.coins, c.name),
            )

        if game_state.supply.get(choice.name, 0) <= 0:
            return
        game_state.supply[choice.name] -= 1
        gained = game_state.gain_card(player, choice)

        # Move from discard/deck into hand (Sculptor gains to hand).
        if gained in player.discard:
            player.discard.remove(gained)
            player.hand.append(gained)
        elif gained in player.deck:
            player.deck.remove(gained)
            player.hand.append(gained)

        if gained.is_treasure:
            player.villagers += 1
