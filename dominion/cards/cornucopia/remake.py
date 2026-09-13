from ..base_card import Card, CardCost, CardStats, CardType


class Remake(Card):
    """Trashes up to two cards, gaining cards costing exactly $1 more."""

    def __init__(self):
        super().__init__(
            name="Remake",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        to_trash = player.ai.choose_cards_to_trash(game_state, list(player.hand), 2)
        to_trash = [card for card in to_trash if card in player.hand][:2]

        if len(to_trash) < 2:
            # Allow the AI to decide fewer cards; keep the explicit order chosen
            to_trash = to_trash

        for card in list(to_trash):
            if card not in player.hand:
                continue
            player.hand.remove(card)
            # "Costing exactly $1 more" compares current (modified) costs, so
            # a Bridge in play lets a Copper (cost $0) become a $2 card.
            target_cost = game_state.get_card_cost(player, card) + 1
            game_state.trash_card(player, card)
            self._gain_card_costing_exactly(game_state, player, target_cost)

    def _gain_card_costing_exactly(self, game_state, player, cost):
        if cost < 0:
            return

        options = []
        from ..registry import get_card

        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            candidate = get_card(name)
            if (
                game_state.get_card_cost(player, candidate) == cost
                and candidate.cost.potions == 0
                and candidate.cost.debt == 0
            ):
                options.append(candidate)

        if not options:
            return

        choice = player.ai.choose_buy(game_state, options + [None])
        if choice is None:
            # The gain is mandatory. When the strategy wants none of the
            # options, take the least harmful: an Action or Treasure over
            # a Victory card or Curse.
            choice = min(
                options,
                key=lambda c: (c.name == "Curse", c.is_victory, -c.cost.coins, c.name),
            )

        if game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice)
