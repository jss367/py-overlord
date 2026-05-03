"""Mining Road from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class MiningRoad(Card):
    """$4 Treasure.

    +1 Buy, +$1. The next time you gain a non-Victory card during your buy
    phase this turn, you may play a Treasure card from your hand: gain a
    card costing exactly $1 more than that Treasure.
    """

    def __init__(self):
        super().__init__(
            name="Mining Road",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1, buys=1),
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

        # This is an eligible gain — consume the one-shot trigger now,
        # regardless of whether the player can or wants to use the effect.
        self._gain_reaction_armed = False

        treasures = [c for c in owner.hand if c.is_treasure]
        if not treasures:
            return

        chosen = owner.ai.mining_road_play_treasure(
            game_state, owner, list(treasures), gained_card
        )
        if chosen is None or chosen not in owner.hand:
            return

        target_cost = chosen.cost.coins + 1
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

        # Play the treasure (it goes to in_play and grants its coin).
        owner.hand.remove(chosen)
        owner.in_play.append(chosen)
        chosen.on_play(game_state)

        game_state.supply[choice.name] -= 1
        game_state.gain_card(owner, choice)

    def on_discard_from_play(self, game_state, player):
        self._gain_reaction_armed = False
        self._owner = None
