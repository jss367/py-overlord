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
        # Allowlist: only iterate names that are real Supply piles. The
        # engine populates ``original_kingdom_pile_names`` with the kingdom
        # cards (and split-pile partners, Castle ranks, Bane). Ruins is
        # technically a Supply pile in Looter games but isn't tracked
        # there, so we add it explicitly when the ordered pile exists.
        # Everything else in ``state.supply`` (Travellers like Treasure
        # Hunter / Warrior / Soldier / Disciple, Joust Rewards, Madman,
        # Mercenary, Spoils, Horse, Spirits, Wishes, Bats, Zombies,
        # Tournament Prizes) is non-Supply and must be skipped.
        allowed = set(getattr(game_state, "original_kingdom_pile_names", set()))
        if "Ruins" in game_state.pile_order:
            allowed.add("Ruins")
        for name in allowed:
            count = game_state.supply.get(name, 0)
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

        # Resolve the supply pile to decrement and the actual card name to
        # gain. For Knights / Ruins the supply count lives under the pile
        # name; the chosen card is the specific top of ``pile_order``.
        pile_name = choice.name
        gain_target_name = choice.name
        ordered_pile = False
        if choice.is_knight and "Knights" in game_state.pile_order:
            pile_name = "Knights"
            order = game_state.pile_order.get("Knights") or []
            if not order:
                return
            gain_target_name = order[-1]
            ordered_pile = True
        elif choice.is_ruins and "Ruins" in game_state.pile_order:
            pile_name = "Ruins"
            order = game_state.pile_order.get("Ruins") or []
            if not order:
                return
            gain_target_name = order[-1]
            ordered_pile = True
        if game_state.supply.get(pile_name, 0) <= 0:
            return

        # For ordered piles, pop ``pile_order`` BEFORE calling ``gain_card``
        # so a Changeling exchange (which appends back to ``pile_order``)
        # does not produce a duplicate top entry. If a replacement happens
        # that the engine doesn't heal (Trader, Exile-reclaim), we push
        # back ourselves below.
        game_state.supply[pile_name] -= 1
        if ordered_pile:
            game_state.pile_order[pile_name].pop()

        # Route through gain_card so reactions (Watchtower / Royal Seal /
        # Trader) and on-gain hooks (Groundskeeper, projects, Falconer,
        # Changeling exchange, etc.) all fire normally. Only move the card
        # from discard to the Summon set-aside zone — if the gain was
        # redirected to the deck (Royal Seal, Tiara, Insignia, Travelling
        # Fair, Watchtower-topdeck) or to the trash (Watchtower-trash) or
        # to Exile, the player's chosen destination is honored and
        # Summon's "play it next turn" effect has no card to play.
        passed_card = get_card(gain_target_name)
        supply_before_gain = game_state.supply.get(pile_name, 0)
        gained = game_state.gain_card(player, passed_card)

        if ordered_pile and gained is not passed_card:
            # Replacement happened (Trader / Exile-reclaim / Changeling).
            # Identity check distinguishes from a normal gain: same-name
            # Exile reclaim returns the prior exiled instance; Trader
            # returns a fresh Silver; Changeling returns a fresh Changeling.
            # Restore the pile ONLY if the engine didn't already — Changeling
            # appends back to ``pile_order`` and bumps ``supply[pile_name]``,
            # while Trader / Exile-reclaim's restoration keys off the variant
            # name (e.g. "Sir Martin"), which isn't in ``state.supply`` for
            # ordered piles, and so doesn't heal.
            if game_state.supply.get(pile_name, 0) == supply_before_gain:
                game_state.pile_order[pile_name].append(gain_target_name)
                game_state.supply[pile_name] = supply_before_gain + 1

        if gained in player.discard:
            player.discard.remove(gained)
            player.summon_set_aside.append(gained)
