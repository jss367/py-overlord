"""Displace - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Displace(Card):
    """Exile a card from your hand. Gain a differently named card costing up
    to $2 more than it.
    """

    def __init__(self):
        super().__init__(
            name="Displace",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return

        choice = player.ai.choose_card_to_exile_for_sanctuary(
            game_state, player, list(player.hand)
        )
        if choice is None or choice not in player.hand:
            choice = min(player.hand, key=self._exile_priority)
        if choice is None or choice not in player.hand:
            return

        # Compute the upgrade ceiling using the exiled card's effective cost
        # (so Bridge/Highway/etc. discounts on the exiled card apply), and
        # match the potion/debt dimensions against printed cost as Dominion's
        # cost rules require those to be respected exactly.
        max_cost = game_state.get_card_cost(player, choice) + 2
        max_potions = choice.cost.potions
        max_debt = choice.cost.debt

        player.hand.remove(choice)
        player.exile.append(choice)

        # Track the supply pile each candidate is drawn from, since ordered
        # piles (Knights, Ruins) gain via the pile placeholder name even
        # though the actual gained card is the visible top of the pile.
        options: list = []
        pile_for_card: dict[int, str] = {}
        # Non-Supply piles live in game_state.supply for lookup convenience
        # but are not legal targets for gain-from-Supply effects. Most are
        # filtered by may_be_bought=False, but a few (notably the Menagerie
        # Horse pile) are unflagged and need an explicit blocklist that
        # mirrors the Black Market deck-builder exclusions.
        non_supply_blocklist = game_state.non_supply_pile_names | {"Horse"}
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            if name in non_supply_blocklist:
                continue
            if name in game_state.pile_order:
                candidate = game_state.top_of_pile(name)
                if candidate is None:
                    continue
                # Individual Knight/Ruins cards return may_be_bought=False
                # because direct supply access uses the pile placeholder;
                # the pile itself is the gainable entry. Skip the per-card
                # check for ordered piles.
            else:
                try:
                    candidate = get_card(name)
                except ValueError:
                    continue
                # Apply structural pile-accessibility restrictions, but
                # NOT general may_be_bought rules — gain effects ignore
                # buy-only conditions (e.g. Grand Market with Copper in
                # play is still gainable).
                #
                # Split piles: bottom card is inaccessible while its
                # partner top card is present.
                if getattr(candidate, "bottom", False):
                    partner = getattr(candidate, "partner_card_name", "")
                    if partner and game_state.supply.get(partner, 0) > 0:
                        continue
                # Allies split piles (Wizards/_split_base) expose multiple
                # upper partners.
                upper_partners = getattr(candidate, "upper_partners", None)
                if upper_partners and any(
                    game_state.supply.get(p, 0) > 0 for p in upper_partners
                ):
                    continue
                # Castles: only the next-in-order Castle is gainable; the
                # may_be_bought check enforces the structural ordering.
                if candidate.is_castle and not candidate.may_be_bought(
                    game_state
                ):
                    continue
            if candidate.name == choice.name:
                continue
            if game_state.get_card_cost(player, candidate) > max_cost:
                continue
            if candidate.cost.potions > max_potions:
                continue
            if candidate.cost.debt > max_debt:
                continue
            options.append(candidate)
            pile_for_card[id(candidate)] = name

        if not options:
            return

        gain_choice = player.ai.choose_buy(game_state, options + [None])
        if gain_choice is None or gain_choice not in options:
            options.sort(
                key=lambda c: (c.cost.coins, c.cost.potions, c.stats.cards, c.name),
                reverse=True,
            )
            gain_choice = options[0]

        pile_name = pile_for_card.get(id(gain_choice), gain_choice.name)
        if game_state.supply.get(pile_name, 0) <= 0:
            return
        game_state.supply[pile_name] -= 1
        is_ordered_pile = pile_name in game_state.pile_order
        if is_ordered_pile and game_state.pile_order[pile_name]:
            game_state.pile_order[pile_name].pop()
        # Snapshot the pile state immediately after decrement+pop so we can
        # tell, post-gain, whether something else restored the pile already.
        post_decrement_supply = game_state.supply[pile_name]
        post_decrement_order_len = (
            len(game_state.pile_order[pile_name]) if is_ordered_pile else 0
        )
        gained = game_state.gain_card(player, gain_choice)
        # gain_card's Trader-replacement and Exile-reclamation paths both
        # try to restore the Supply via gain_choice.name, which for
        # ordered piles (Knights, Ruins) is the specific top card (e.g.
        # "Dame Josephine") rather than the pile placeholder, so the
        # restore silently no-ops there. Changeling's exchange, in
        # contrast, restores the pile placeholder directly. We treat any
        # case where gain_card returned a different object as
        # potentially needing a manual restore, then use the post-
        # decrement snapshot to skip the Changeling case (where the
        # pile state was already restored for us).
        if (
            is_ordered_pile
            and gained is not None
            and gained is not gain_choice
            and game_state.supply.get(pile_name, 0) == post_decrement_supply
            and len(game_state.pile_order.get(pile_name, []))
            == post_decrement_order_len
        ):
            game_state.supply[pile_name] = game_state.supply.get(pile_name, 0) + 1
            game_state.pile_order.setdefault(pile_name, []).append(gain_choice.name)

    @staticmethod
    def _exile_priority(card):
        if card.name == "Curse":
            return (0, card.cost.coins, card.name)
        if card.is_victory and not card.is_action:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.cost.coins, card.name)
        return (3, card.cost.coins, card.name)
