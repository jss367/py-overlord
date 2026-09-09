from ..base_card import Card, CardCost, CardStats, CardType


class Wheelwright(Card):
    """+1 Card, +1 Action. You may discard a card to gain an Action card
    costing as much as it or less.

    The discard is optional, but once a card is discarded the gain is
    mandatory when any Action card of that cost or less is in the Supply.
    The AI picks the discard through ``choose_wheelwright_discard``; its
    default only offers dead cards (Curses, pure Victory cards) plus Coppers
    when the strategy actually wants a $0 Action. Whether the gain happens
    at all is driven by the AI's gain choice, so a strategy that wants no
    $2 Action will not throw away an Estate to gain one.
    """

    def __init__(self):
        super().__init__(
            name="Wheelwright",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    @staticmethod
    def _gainable_actions(game_state, player, max_cost: int) -> list:
        from ..registry import get_card

        options = []
        for name, count in game_state.supply.items():
            if count <= 0 or name in game_state.non_supply_pile_names:
                continue
            candidate = get_card(name)
            if not candidate.is_action:
                continue
            if candidate.cost.potions or candidate.cost.debt:
                continue
            if game_state.get_card_cost(player, candidate) <= max_cost:
                options.append(candidate)
        return options

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        # Ask the AI which card it would discard; it may decline (None).
        # For each candidate in preference order, offer the gainable Actions;
        # the first candidate whose gain the AI actually wants is discarded.
        candidates = player.ai.choose_wheelwright_discard(
            game_state, player, list(player.hand)
        )
        if candidates is None:
            return
        if isinstance(candidates, Card):
            candidates = [candidates]

        for discard in candidates:
            if discard not in player.hand:
                continue
            max_cost = game_state.get_card_cost(player, discard)
            options = self._gainable_actions(game_state, player, max_cost)
            if not options:
                continue
            gain_choice = player.ai.choose_buy(game_state, options + [None])
            if gain_choice is None or gain_choice.name not in {o.name for o in options}:
                continue
            if game_state.supply.get(gain_choice.name, 0) <= 0:
                continue

            player.hand.remove(discard)
            game_state.discard_card(player, discard)
            game_state.supply[gain_choice.name] -= 1
            game_state.gain_card(player, gain_choice)
            return
