"""Way of the Chameleon — Follow the card's instructions, swapping +Cards
and +$ (each ``+Cards`` becomes ``+$`` and vice versa).

Important: the swap applies ONLY to instructions on the chosen card itself
that are written as "+Cards" or "+$". It does NOT apply to:

- Imperative draws like "draw until you have 6 cards in hand" (Cursed
  Village) or "set aside the top card; draw it" (Library) — these are
  not "+Cards" instructions.
- Imperative coin gains that aren't "+$" wording.
- Cards played as a side effect of the chosen card (e.g. Vassal -> Action,
  Throne Room -> Action). Those run their own normal effects.

To support cards whose "+Cards"/"+$" appears in ``play_effect`` (because
the value depends on a choice or condition), play_effect bodies use the
helpers ``chameleon_plus_cards`` / ``chameleon_plus_coins`` exposed below.
When a chameleon swap is active (depth 1 of the chosen card) those
helpers route the value into the swap accumulator; otherwise they fall
back to ``draw_cards`` / ``player.coins +=`` exactly as before.
"""

from contextlib import contextmanager

from .base_way import Way


# Module-level state for the active chameleon swap. Only one swap is
# active at a time (the outer-card resolution); nested plays don't swap.
_active_state: dict | None = None


def _chameleon_is_active(player) -> bool:
    """Return True when a Chameleon swap is in progress for ``player``.

    Only depth-1 (the chosen outer card itself) participates in the swap;
    nested plays (Vassal->Village, Throne Room->Smithy, etc.) don't.
    """
    s = _active_state
    return bool(s and s["player"] is player and s["depth"] == 1)


def chameleon_plus_cards(game_state, player, count: int) -> None:
    """Imperative ``+Cards`` instruction in a card's ``play_effect``.

    Use this in play_effect bodies for "+Cards" wording (the value is
    written on the card as ``+Cards``). Do NOT use it for imperative
    draws like "draw until you have 6 in hand" or "draw the set-aside
    card" — those are not ``+Cards`` instructions and must not swap.

    When a Chameleon swap is active on this player, the count is
    captured for later conversion to ``+$``. Otherwise the cards are
    drawn normally.
    """
    if count <= 0:
        return
    if _chameleon_is_active(player):
        _active_state["cards_requested"] += count  # type: ignore[index]
        return
    game_state.draw_cards(player, count)


def chameleon_plus_coins(player, amount: int) -> None:
    """Imperative ``+$`` instruction in a card's ``play_effect``.

    Use this in play_effect bodies for "+$" wording (the amount is
    written on the card as ``+$``). Do NOT use it for non-``+$`` coin
    gains.

    When a Chameleon swap is active on this player, the amount is
    captured for later conversion to ``+Cards``. Otherwise the coins
    are added normally.
    """
    if amount <= 0:
        return
    if _chameleon_is_active(player):
        _active_state["coins_requested"] += amount  # type: ignore[index]
        return
    player.coins += amount


@contextmanager
def chameleon_swap_block(game_state, player):
    """Optional context manager wrapping a block of ``+Cards``/``+$``
    instructions inside a play_effect. Inside the block,
    ``game_state.draw_cards`` and ``player.coins +=`` style operations
    are still NOT auto-swapped — callers must use ``chameleon_plus_cards``
    / ``chameleon_plus_coins`` to express +Cards/+$ explicitly. The
    context manager exists for clarity; it is a no-op today and reserved
    for future use.
    """
    yield


class WayOfTheChameleon(Way):
    def __init__(self):
        super().__init__("Way of the Chameleon")

    def apply(self, game_state, card) -> None:
        global _active_state

        player = game_state.current_player

        # Patch Card.on_play to:
        #   - at depth 1 (the chosen card itself) skip the stat-block
        #     +Cards and +$ (capture them for the swap), then run
        #     play_effect — which may further accumulate via the
        #     chameleon_plus_cards / chameleon_plus_coins helpers.
        #   - at depth >= 2 (any nested play caused by the chosen card)
        #     run the ORIGINAL on_play with no patches: nested cards keep
        #     their real effects and don't see the chameleon swap.
        from dominion.cards.base_card import Card

        original_on_play = Card.on_play

        prev_state = _active_state
        state: dict = {
            "player": player,
            "depth": 0,
            "cards_requested": 0,
            "coins_requested": 0,
        }

        def wrapped_on_play(self_card, gs):
            state["depth"] += 1
            try:
                if state["depth"] == 1:
                    # Capture the chosen card's stat-block ``+Cards`` and
                    # ``+$`` for the swap, then temporarily zero them so
                    # the card's *actual* ``on_play`` runs every other
                    # effect (overridden ``on_play`` bodies, ``play_effect``
                    # subclass code, etc.) without re-applying them.
                    #
                    # Cards that move their ``+Cards`` / ``+$`` wording
                    # into ``on_play`` / ``play_effect`` (e.g. Bauble's
                    # "+$1" choice, Contract's "+$2", Hunting Lodge's
                    # "+5 Cards" branch) should call the helpers
                    # ``chameleon_plus_cards`` / ``chameleon_plus_coins``;
                    # those route through the swap accumulator while a
                    # swap is active.
                    if self_card.stats.cards > 0:
                        state["cards_requested"] += self_card.stats.cards
                    if self_card.stats.coins > 0:
                        state["coins_requested"] += self_card.stats.coins

                    saved_cards = self_card.stats.cards
                    saved_coins = self_card.stats.coins
                    self_card.stats.cards = 0
                    self_card.stats.coins = 0
                    try:
                        # Run the card's real ``on_play`` (which may be
                        # overridden by the subclass — e.g. Bauble,
                        # Contract). Stat-block ``+Cards`` and ``+$`` are
                        # zeroed out for the duration of this call so they
                        # don't double-apply alongside the swap.
                        #
                        # Use the subclass's MRO-resolved ``on_play`` so
                        # that overrides (Bauble, Contract, ...) run their
                        # full body. ``Card.on_play`` is currently patched
                        # to ``wrapped_on_play``; subclasses that define
                        # their own ``on_play`` are unaffected by that
                        # patch and resolve to their override directly.
                        cls_on_play = type(self_card).on_play
                        if cls_on_play is wrapped_on_play:
                            # No subclass override — use the original
                            # ``Card.on_play`` body.
                            original_on_play(self_card, gs)
                        else:
                            cls_on_play(self_card, gs)
                    finally:
                        self_card.stats.cards = saved_cards
                        self_card.stats.coins = saved_coins
                else:
                    # Nested play: run the unpatched original on_play so
                    # the nested card's +Cards / +$ are NOT swapped.
                    cls_on_play = type(self_card).on_play
                    if cls_on_play is wrapped_on_play:
                        original_on_play(self_card, gs)
                    else:
                        cls_on_play(self_card, gs)
            finally:
                state["depth"] -= 1

        Card.on_play = wrapped_on_play  # type: ignore[assignment]
        _active_state = state
        card._chameleon_active = True
        try:
            wrapped_on_play(card, game_state)
        finally:
            Card.on_play = original_on_play  # type: ignore[assignment]
            _active_state = prev_state
            card._chameleon_active = False

        cards_requested = state["cards_requested"]
        coins_requested = state["coins_requested"]

        # Apply the swap: captured +Cards become +$, captured +$ become
        # the same number of drawn cards.
        if coins_requested > 0:
            game_state.draw_cards(player, coins_requested)
        if cards_requested > 0:
            player.coins += cards_requested
