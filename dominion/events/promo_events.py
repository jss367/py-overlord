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
        candidates: list = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            # Dark Ages: ordered piles ("Knights", "Ruins") expose a
            # placeholder under their pile name. Resolve to the actual top
            # card via ``top_of_pile`` so Summon sees the real Action that
            # would be gained, not the placeholder.
            if name in game_state.pile_order:
                card = game_state.top_of_pile(name)
                if card is None:
                    continue
            else:
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
        if choice is None:
            return

        # Resolve the supply pile to decrement. For Knights / Ruins the
        # supply count lives under the pile name; the chosen card is the
        # specific top card whose name must be popped off pile_order.
        pile_name = choice.name
        gain_target_name = choice.name
        if choice.is_knight and "Knights" in game_state.pile_order:
            pile_name = "Knights"
            order = game_state.pile_order.get("Knights") or []
            if not order:
                return
            gain_target_name = order.pop()
        elif choice.is_ruins and "Ruins" in game_state.pile_order:
            pile_name = "Ruins"
            order = game_state.pile_order.get("Ruins") or []
            if not order:
                return
            gain_target_name = order.pop()
        if game_state.supply.get(pile_name, 0) <= 0:
            return

        # Route through gain_card so reactions (Watchtower / Royal Seal /
        # Trader) and on-gain hooks (Groundskeeper, projects, Falconer, etc.)
        # all fire normally. Only move the card from discard to the Summon
        # set-aside zone — if the gain was redirected to the deck (Royal
        # Seal, Tiara, Insignia, Travelling Fair, Watchtower-topdeck) or
        # to the trash (Watchtower-trash) or to Exile, the player's chosen
        # destination is honored and Summon's "play it next turn" effect
        # has no card to play.
        game_state.supply[pile_name] -= 1
        gained = game_state.gain_card(player, get_card(gain_target_name))
        if gained in player.discard:
            player.discard.remove(gained)
            player.summon_set_aside.append(gained)
