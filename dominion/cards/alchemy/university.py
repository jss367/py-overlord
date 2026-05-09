"""University - Action from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class University(Card):
    """Action ($2P): +2 Actions. You may gain an Action card costing up to $5."""

    def __init__(self):
        super().__init__(
            name="University",
            cost=CardCost(coins=2, potions=1),
            stats=CardStats(actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        options: list = []
        pile_for_card: dict[int, str] = {}
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
            else:
                try:
                    candidate = get_card(name)
                except ValueError:
                    continue
                if not candidate.may_be_gained(game_state):
                    continue
            if not candidate.is_action:
                continue
            if candidate.cost.potions > 0:
                continue
            if candidate.cost.debt > 0:
                continue
            if game_state.get_card_cost(player, candidate) > 5:
                continue
            options.append(candidate)
            pile_for_card[id(candidate)] = name

        if not options:
            return

        choice = player.ai.choose_buy(game_state, options + [None])
        if choice is None or choice not in options:
            return

        pile_name = pile_for_card.get(id(choice), choice.name)
        if game_state.supply.get(pile_name, 0) <= 0:
            return
        game_state.supply[pile_name] -= 1
        is_ordered_pile = pile_name in game_state.pile_order
        if is_ordered_pile and game_state.pile_order[pile_name]:
            game_state.pile_order[pile_name].pop()
        # Snapshot pile state immediately after decrement+pop so we can
        # detect, post-gain, whether something else (Changeling) restored
        # the pile already. Mirrors Displace's ordered-pile bookkeeping.
        post_decrement_supply = game_state.supply[pile_name]
        post_decrement_order_len = (
            len(game_state.pile_order[pile_name]) if is_ordered_pile else 0
        )
        gained = game_state.gain_card(player, choice)
        # gain_card's Trader-replacement and Exile-reclamation paths both
        # try to restore the Supply via gained.name, which for ordered
        # piles (Knights, Ruins) is the specific top card name (e.g.
        # "Sir Bailey") rather than the pile placeholder, so the restore
        # silently no-ops there. Manually restore the placeholder pile
        # in that case, but skip when the pile state was already restored
        # for us (e.g. by Changeling's exchange).
        if (
            is_ordered_pile
            and gained is not None
            and gained is not choice
            and game_state.supply.get(pile_name, 0) == post_decrement_supply
            and len(game_state.pile_order.get(pile_name, []))
            == post_decrement_order_len
        ):
            game_state.supply[pile_name] = game_state.supply.get(pile_name, 0) + 1
            game_state.pile_order.setdefault(pile_name, []).append(choice.name)
