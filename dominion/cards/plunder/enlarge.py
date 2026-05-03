"""Enlarge from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Enlarge(Card):
    """$5 Action-Duration: Now and at start of next turn, trash a card from
    hand and gain a card costing up to $2 more.
    """

    def __init__(self):
        super().__init__(
            name="Enlarge",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        self._do_remodel(game_state, player)
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        self._do_remodel(game_state, player)
        self.duration_persistent = False

    @staticmethod
    def _do_remodel(game_state, player):
        from ..registry import get_card

        if not player.hand:
            return

        to_trash = player.ai.choose_card_to_trash(
            game_state, list(player.hand) + [None]
        )
        if to_trash is None or to_trash not in player.hand:
            return

        trashed_cost = game_state.get_card_cost(player, to_trash)
        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)

        max_cost = trashed_cost + 2
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins <= max_cost and card.cost.potions == 0:
                candidates.append(card)

        if not candidates:
            return

        choice = player.ai.choose_buy(game_state, list(candidates) + [None])
        if choice is None or game_state.supply.get(choice.name, 0) <= 0:
            candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            choice = candidates[0]

        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice)
