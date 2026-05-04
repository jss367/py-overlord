from .base_ally import Ally


class ForestDwellers(Ally):
    """At start of turn, spend 1 Favor: look at top 3 cards, choose order.

    Implementation: pull top 3 cards, sort them by Patrol-style priority
    (most useful first to be drawn), and put them back on top. The AI
    then draws them in that order on subsequent draws.
    """

    def __init__(self):
        super().__init__("Forest Dwellers")

    def on_turn_start(self, game_state, player) -> None:
        if player.favors <= 0:
            return
        # Need to actually draw soon; otherwise the order doesn't matter.
        if not (player.deck or player.discard):
            return
        cards = []
        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            cards.append(player.deck.pop())
        if not cards:
            return
        # Order so that the highest-priority card is drawn first
        # (deck.pop() reads from the end, so put best at end).
        ordered = player.ai.order_cards_for_topdeck(game_state, player, list(cards))
        # Reverse: best at top of deck.
        for card in reversed(ordered):
            player.deck.append(card)
        player.favors -= 1
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                "spends a Favor on Forest Dwellers (reorder top 3)",
                {"favors_remaining": player.favors},
            )
        )
