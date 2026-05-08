"""Implementation of the Promo Events."""

from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card

from .base_event import Event


class Summon(Event):
    """$5 — Gain an Action card costing up to $4. Set it aside, and at the
    start of your next turn, play it.
    """

    def __init__(self):
        super().__init__("Summon", CardCost(coins=5))

    def on_buy(self, game_state, player) -> None:
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action:
                continue
            if card.cost.potions or card.cost.debt:
                continue
            if game_state.get_card_cost(player, card) > 4:
                continue
            candidates.append(card)
        if not candidates:
            return
        choice = player.ai.choose_gain_for_summon(game_state, player, candidates)
        if choice is None or game_state.supply.get(choice.name, 0) <= 0:
            return
        # Route through gain_card so reactions (Watchtower / Royal Seal /
        # Trader) and on-gain hooks (Groundskeeper, projects, Falconer, etc.)
        # all fire normally. Then move whatever ended up in discard/deck to
        # the Summon set-aside zone so it gets played at the start of the
        # next turn. If the gain was diverted (Watchtower trash, Exile),
        # the card stays where it landed and Summon's "play it" effect just
        # has nothing to do.
        game_state.supply[choice.name] -= 1
        gained = game_state.gain_card(player, get_card(choice.name))
        if gained in player.discard:
            player.discard.remove(gained)
            player.summon_set_aside.append(gained)
        elif gained in player.deck:
            player.deck.remove(gained)
            player.summon_set_aside.append(gained)
