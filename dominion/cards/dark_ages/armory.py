"""Armory ($4): gain a card onto your deck costing up to $4."""

from ..base_card import Card, CardCost, CardStats, CardType


class Armory(Card):
    def __init__(self):
        super().__init__(
            name="Armory",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..adventures.artificer import _exposed_supply_card

        player = game_state.current_player
        options = []
        for pile_name in list(game_state.supply):
            card = _exposed_supply_card(game_state, pile_name)
            if card is None:
                continue
            if card.cost.potions > 0 or card.cost.debt > 0:
                continue
            if game_state.get_card_cost(player, card) <= 4:
                options.append(card)

        if not options:
            return

        chosen = player.ai.choose_armory_gain(game_state, player, options)
        if chosen is None or chosen not in options:
            # The gain is mandatory ("Gain a card onto your deck costing up
            # to $4"), so a declining or invalid hook falls back to the
            # shared ranking rather than gaining nothing.
            chosen = max(options, key=lambda c: (c.cost.coins, c.stats.cards, c.name))
        gained = game_state.take_top_supply_card(game_state.supply_pile_key(chosen.name))
        if gained is None:
            return
        game_state.gain_card(player, gained, to_deck=True)
