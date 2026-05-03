"""Mining Road from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class MiningRoad(Card):
    """$4 Treasure: +1 Action, +1 Buy, +$1.

    The next time you gain a non-Victory card during your buy phase this turn,
    you may set aside a Treasure card from your hand: gain a card costing
    exactly $1 more than that Treasure (this turn).
    """

    def __init__(self):
        super().__init__(
            name="Mining Road",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, coins=1, buys=1),
            types=[CardType.TREASURE],
        )
        self._owner = None
        self._gain_reaction_armed = False

    def play_effect(self, game_state):
        player = game_state.current_player
        self._owner = player
        self._gain_reaction_armed = True

    def on_card_gained(self, game_state, owner, gainer, gained_card):
        from ..registry import get_card

        if not self._gain_reaction_armed:
            return
        if owner is not self._owner or gainer is not self._owner:
            return
        if gained_card.is_victory:
            return
        if game_state.phase != "buy":
            return

        treasures = [c for c in owner.hand if c.is_treasure]
        if not treasures:
            return

        chosen_treasure = owner.ai.choose_treasure(
            game_state, list(treasures) + [None]
        )
        if chosen_treasure is None or chosen_treasure not in owner.hand:
            return

        target_cost = chosen_treasure.cost.coins + 1
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins == target_cost and card.cost.potions == 0:
                candidates.append(card)

        if not candidates:
            return

        choice = owner.ai.choose_buy(game_state, list(candidates) + [None])
        if choice is None or game_state.supply.get(choice.name, 0) <= 0:
            return

        self._gain_reaction_armed = False

        owner.hand.remove(chosen_treasure)
        owner.in_play.append(chosen_treasure)

        game_state.supply[choice.name] -= 1
        game_state.gain_card(owner, choice)

    def on_discard_from_play(self, game_state, player):
        self._gain_reaction_armed = False
        self._owner = None
