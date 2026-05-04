"""Way of the Chameleon — Follow the card's instructions, swapping +Cards
and +$ (each ``+Cards`` becomes ``+$`` and vice versa).
"""

from .base_way import Way


class WayOfTheChameleon(Way):
    def __init__(self):
        super().__init__("Way of the Chameleon")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player

        # Record coin total before play so we can detect both stat-driven and
        # imperative ``player.coins += N`` increments while the card resolves.
        coins_before = player.coins

        # Intercept ``game_state.draw_cards`` while this card resolves so
        # imperative draws (e.g. inside ``play_effect``) are also swapped, not
        # just the stat-driven ``+Cards``. We accumulate the requested counts
        # and convert them to ``+$`` after the play resolves.
        original_draw_cards = game_state.draw_cards
        cards_requested = 0

        def counting_draw_cards(p, count, *args, **kwargs):
            nonlocal cards_requested
            if p is player and count > 0:
                cards_requested += count
                return []
            return original_draw_cards(p, count, *args, **kwargs)

        game_state.draw_cards = counting_draw_cards  # type: ignore[assignment]
        card._chameleon_active = True
        try:
            card.on_play(game_state)
            # Note: Ally hooks are fired by the Action phase loop after
            # ``way.apply`` returns.
        finally:
            game_state.draw_cards = original_draw_cards  # type: ignore[assignment]
            card._chameleon_active = False

        # Total ``+$`` the card produced (stat-driven + imperative) becomes
        # ``+Cards``; total ``+Cards`` requested becomes ``+$``.
        coins_added = player.coins - coins_before
        if coins_added:
            player.coins -= coins_added
        if cards_requested:
            player.coins += cards_requested
        if coins_added > 0:
            original_draw_cards(player, coins_added)
