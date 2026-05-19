from ..base_card import Card, CardCost, CardStats, CardType


class Rebuild(Card):
    def __init__(self):
        super().__init__(
            name="Rebuild",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        named = self._named_card(game_state, player)

        revealed = []
        trashed = None
        while True:
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break

            card = player.deck.pop()
            revealed.append(card)
            if card.is_victory and card.name != named:
                trashed = card
                break

        for card in revealed:
            if card is trashed:
                continue
            game_state.discard_card(player, card)

        if trashed is None:
            return

        game_state.trash_card(player, trashed)
        self._gain_replacement(game_state, player, trashed)

    @staticmethod
    def _named_card(game_state, player) -> str:
        chooser = getattr(player.ai, "choose_name_for_rebuild", None)
        if chooser is not None:
            choice = chooser(game_state, player)
            if isinstance(choice, str) and choice:
                return choice

        # Default: protect Provinces once Rebuild finds them; otherwise turn
        # the first lower Victory card into the best available upgrade.
        return "Province"

    def _gain_replacement(self, game_state, player, trashed):
        options, pile_for_card = self._gain_options(game_state, player, trashed)
        if not options:
            return

        choice = self._choose_gain(game_state, player, options)
        pile_name = pile_for_card.get(id(choice), choice.name)
        if game_state.supply.get(pile_name, 0) <= 0:
            return

        game_state.supply[pile_name] -= 1
        is_ordered_pile = pile_name in game_state.pile_order
        if is_ordered_pile and game_state.pile_order[pile_name]:
            game_state.pile_order[pile_name].pop()

        post_decrement_supply = game_state.supply[pile_name]
        post_decrement_order_len = (
            len(game_state.pile_order[pile_name]) if is_ordered_pile else 0
        )
        gained = game_state.gain_card(player, choice)
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

    @staticmethod
    def _gain_options(game_state, player, trashed):
        from ..registry import get_card

        max_coins = game_state.get_card_cost(player, trashed) + 3
        max_potions = trashed.cost.potions
        max_debt = trashed.cost.debt
        options = []
        pile_for_card = {}
        non_supply_blocklist = game_state.non_supply_pile_names | {"Horse"}

        for name, count in game_state.supply.items():
            if count <= 0 or name in non_supply_blocklist:
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

            if not candidate.is_victory:
                continue
            if game_state.get_card_cost(player, candidate) > max_coins:
                continue
            if candidate.cost.potions > max_potions:
                continue
            if candidate.cost.debt > max_debt:
                continue

            options.append(candidate)
            pile_for_card[id(candidate)] = name

        return options, pile_for_card

    @staticmethod
    def _choose_gain(game_state, player, options):
        chooser = getattr(player.ai, "choose_card_to_gain_for_rebuild", None)
        choice = chooser(game_state, player, list(options)) if chooser else None

        if choice is None:
            choice = player.ai.choose_buy(game_state, list(options) + [None])

        if choice in options:
            return choice

        choice_name = getattr(choice, "name", None)
        if choice_name is not None:
            for option in options:
                if option.name == choice_name:
                    return option

        return max(
            options,
            key=lambda card: (
                game_state.get_card_cost(player, card),
                card.cost.potions,
                card.cost.debt,
                card.stats.vp,
                card.name,
            ),
        )
