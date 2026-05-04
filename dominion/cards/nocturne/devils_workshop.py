"""Devil's Workshop — $4 Night.

If you've gained 0 cards this turn: gain a card costing up to $4.
If 1: gain a Gold. If 2+: gain an Imp.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class DevilsWorkshop(Card):
    nocturne_piles = {"Imp": 13}

    def __init__(self):
        super().__init__(
            name="Devil's Workshop",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.NIGHT],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        gained = getattr(player, "cards_gained_this_turn_count", 0)

        if gained >= 2:
            if game_state.supply.get("Imp", 0) > 0:
                game_state.supply["Imp"] -= 1
                game_state.gain_card(player, get_card("Imp"))
            return
        if gained == 1:
            if game_state.supply.get("Gold", 0) > 0:
                game_state.supply["Gold"] -= 1
                game_state.gain_card(player, get_card("Gold"))
            return

        # Gained 0 — pick a card up to $4
        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins > 4 or card.cost.potions > 0 or card.cost.debt > 0:
                continue
            if not card.may_be_bought(game_state):
                continue
            options.append(card)
        if not options:
            return
        choice = player.ai.choose_card_to_gain_up_to(game_state, player, options, 4)
        if choice is None:
            choice = max(options, key=lambda c: (c.cost.coins, c.stats.cards, c.name))
        if game_state.supply.get(choice.name, 0) > 0:
            game_state.supply[choice.name] -= 1
            game_state.gain_card(player, choice)
