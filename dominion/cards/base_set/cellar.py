"""Implementation of the Cellar discard-and-draw card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Cellar(Card):
    """Action ($2): +1 Action. Discard any number of cards, then draw that many."""

    def __init__(self):
        super().__init__(
            name="Cellar",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.hand:
            return

        # Default heuristic: discard any obviously low-value card (Curse, junk
        # Victory, Copper). The AI hook can override via choose_cards_to_discard
        # with a count equal to the hand size and ``reason="cellar"``.
        max_discard = len(player.hand)
        selected = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), max_discard, reason="cellar"
        )

        # Filter selection to junky cards only when the AI returned everything
        # (the default discard heuristic returns up to ``count`` items even if
        # they aren't all junk). This avoids the AI accidentally discarding a
        # premium hand for Cellar's redraw.
        if len(selected) == max_discard:
            selected = [c for c in selected if self._is_junk(c)]

        discarded = 0
        for card in selected:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                discarded += 1

        if discarded > 0:
            game_state.draw_cards(player, discarded)

    @staticmethod
    def _is_junk(card) -> bool:
        if card.name == "Curse":
            return True
        if card.name == "Copper":
            return True
        if card.is_victory and not card.is_action and card.cost.coins <= 2:
            return True
        return False
