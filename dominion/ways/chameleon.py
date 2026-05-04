"""Way of the Chameleon — Follow the card's instructions, swapping +Cards
and +$ (each ``+Cards`` becomes ``+$`` and vice versa).
"""

from .base_way import Way


class WayOfTheChameleon(Way):
    def __init__(self):
        super().__init__("Way of the Chameleon")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player

        # The Way only swaps the chosen card's OWN +Cards and +$ — not the
        # effects of cards that this card causes to be played as a side effect
        # (e.g. Vassal -> Village, Throne Room -> X, Imp/Conclave -> Action,
        # Procession -> Action). To enforce that, we wrap ``Card.on_play`` for
        # the duration of this resolution and track the play depth: only the
        # outermost play (depth 1) is swapped; nested plays (depth >= 2) run
        # with the un-intercepted draw/coin pathways and their deltas are
        # subtracted out of the outer card's totals.
        from dominion.cards.base_card import Card

        original_on_play = Card.on_play
        original_draw_cards = game_state.draw_cards

        # Counters mutable across the nested closures.
        state = {
            "depth": 0,
            "cards_requested": 0,  # +Cards requested by the outer card only
            "nested_coins_delta": 0,  # coins added inside nested plays
        }

        def counting_draw_cards(p, count, *args, **kwargs):
            # Only intercept draws for the active player and only while we
            # are resolving the outer chameleon-targeted card itself
            # (depth == 1). Nested plays (Village inside Vassal, etc.) draw
            # normally so their +Cards aren't converted to +$.
            if p is player and count > 0 and state["depth"] == 1:
                state["cards_requested"] += count
                return []
            return original_draw_cards(p, count, *args, **kwargs)

        def wrapped_on_play(self_card, gs):
            state["depth"] += 1
            try:
                if state["depth"] >= 2:
                    # Track coins added during the nested play so we can
                    # exclude them from the outer card's swap.
                    coins_before_nested = player.coins
                    try:
                        original_on_play(self_card, gs)
                    finally:
                        state["nested_coins_delta"] += (
                            player.coins - coins_before_nested
                        )
                else:
                    original_on_play(self_card, gs)
            finally:
                state["depth"] -= 1

        coins_before = player.coins
        Card.on_play = wrapped_on_play  # type: ignore[assignment]
        game_state.draw_cards = counting_draw_cards  # type: ignore[assignment]
        card._chameleon_active = True
        try:
            # Bound-method-style call: wrapped_on_play receives (card, gs).
            wrapped_on_play(card, game_state)
        finally:
            Card.on_play = original_on_play  # type: ignore[assignment]
            game_state.draw_cards = original_draw_cards  # type: ignore[assignment]
            card._chameleon_active = False

        # Coins added by the outer card itself = total delta minus anything
        # added by nested plays (which keep their own effects intact).
        total_coin_delta = player.coins - coins_before
        outer_coins_added = total_coin_delta - state["nested_coins_delta"]
        cards_requested = state["cards_requested"]

        if outer_coins_added:
            player.coins -= outer_coins_added
        if cards_requested:
            player.coins += cards_requested
        if outer_coins_added > 0:
            original_draw_cards(player, outer_coins_added)
