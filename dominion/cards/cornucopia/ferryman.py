from ..base_card import Card, CardCost, CardStats, CardType


class Ferryman(Card):
    """+2 Cards / +1 Action. Discard a card. Setup: choose an unused
    Kingdom card pile costing $3 or $4 — gain one when you gain a
    Ferryman."""

    def __init__(self):
        super().__init__(
            name="Ferryman",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        chosen = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 1, reason="ferryman"
        )
        if not chosen:
            # AI declined; per the rules the discard is mandatory, so
            # fall back to discarding the lowest-priority card.
            chosen = [min(player.hand, key=self._discard_priority)]
        card = chosen[0]
        if card in player.hand:
            player.hand.remove(card)
            game_state.discard_card(player, card)

    @staticmethod
    def _discard_priority(card):
        if card.name == "Curse":
            return (0, card.cost.coins, card.name)
        if card.is_victory and not card.is_action:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.cost.coins, card.name)
        return (3, card.cost.coins, card.name)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        from ..registry import get_card

        # The Ferryman pile may be a split pile; gain the current top of
        # the pile (first non-empty name in pile order). Fall back to
        # ``ferryman_card_name`` if pile order wasn't built (older saves
        # / tests that set up Ferryman directly).
        order = getattr(game_state, "ferryman_pile_order", None) or [
            getattr(game_state, "ferryman_card_name", "")
        ]
        for name in order:
            if not name:
                continue
            if game_state.supply.get(name, 0) <= 0:
                continue
            game_state.supply[name] -= 1
            previous = getattr(game_state, "_allow_ferryman_pile_gain", False)
            game_state._allow_ferryman_pile_gain = True
            try:
                game_state.gain_card(player, get_card(name))
            finally:
                game_state._allow_ferryman_pile_gain = previous
            return
