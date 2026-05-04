"""Implementation of the Transmogrify card from Adventures.

The official card is an Action-Reserve: it sets itself aside on the Tavern
mat, and you may call it at the start of a future turn to trash a card and
gain a card costing up to $1 more (into your hand). This codebase has no
Tavern/Reserve infrastructure, so the simplified implementation here resolves
the trash-and-gain immediately upon playing the card. The +1 Action keeps it
playable mid-turn as a cantrip remodel-into-hand.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Transmogrify(Card):
    def __init__(self):
        super().__init__(
            name="Transmogrify",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
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

        trashed_cost = game_state.get_card_cost(player, to_trash)
        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)

        max_cost = trashed_cost + 1
        candidates = []
        for name, supply_count in game_state.supply.items():
            if supply_count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.potions > 0:
                continue
            if game_state.get_card_cost(player, card) > max_cost:
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
        gained = game_state.gain_card(player, chosen)

        if gained in player.discard:
            player.discard.remove(gained)
            player.hand.append(gained)
        elif gained in player.deck:
            player.deck.remove(gained)
            player.hand.append(gained)
        elif gained not in player.hand:
            player.hand.append(gained)
