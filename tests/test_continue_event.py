"""Tests for the Continue event from Plunder.

Continue's text: "$8: gain a non-Victory non-Command card costing up to $4,
then play it." Two invariants under test:

1. The "play it" clause applies to *any* gained card type (Action or
   Treasure), not just Actions. A gained Silver should be played and add
   its $2 to the player's coin pool.
2. The play step must locate the gained card across all post-gain zones,
   not just ``discard``. If a top-deck reaction (Royal Seal, Insignia, …)
   places the gain on top of the deck, Continue must still find it there
   and move it cleanly into ``in_play`` — leaving the same object in two
   zones would corrupt later cleanup and draw.
"""

from dominion.cards.registry import get_card
from dominion.events.continue_event import Continue
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


class _FixedTargetAI:
    """AI that always picks the named card from Continue's choices."""

    def __init__(self, target_name: str):
        self.name = "fixed"
        self.target_name = target_name
        self.strategy = None

    def choose_action(self, *args, **kwargs):
        return None

    def choose_treasure(self, *args, **kwargs):
        return None

    def choose_buy(self, *args, **kwargs):
        return None

    def choose_card_to_trash(self, *args, **kwargs):
        return None

    def choose_continue_target(self, state, player, choices):
        for c in choices:
            if c.name == self.target_name:
                return c
        return choices[0] if choices else None


def _new_state(target_name: str) -> tuple[GameState, PlayerState]:
    state = GameState(players=[])
    state.players = [PlayerState(_FixedTargetAI(target_name))]
    state.setup_supply([get_card("Village")])
    state.players[0].coins = 8
    return state, state.players[0]


def test_continue_plays_a_gained_treasure():
    """Gaining Silver via Continue should add $2 to the coin pool."""
    state, player = _new_state("Silver")
    coins_before = player.coins
    Continue().on_buy(state, player)
    # Silver is in_play and contributed +$2.
    assert any(c.name == "Silver" for c in player.in_play), "Silver should be in_play after Continue"
    assert player.coins == coins_before + 2, f"Silver should add $2; got {player.coins - coins_before}"


def test_continue_does_not_duplicate_topdecked_gains():
    """If Insignia tops-decks the gain, Continue must still find and play it
    cleanly without leaving the same object in both deck and in_play."""
    state, player = _new_state("Village")
    player.insignia_active = True
    # Make the AI accept top-decking.
    player.ai.should_topdeck_with_insignia = lambda *a, **k: True

    Continue().on_buy(state, player)

    # Locate the Village. It should be in_play exactly once and not in deck.
    villages_in_play = [c for c in player.in_play if c.name == "Village"]
    villages_in_deck = [c for c in player.deck if c.name == "Village"]
    villages_in_discard = [c for c in player.discard if c.name == "Village"]
    assert len(villages_in_play) == 1, f"Village should be in_play once; in_play has {len(villages_in_play)}"
    assert villages_in_deck == [], f"Village should not be left on deck; got {len(villages_in_deck)}"
    assert villages_in_discard == [], f"Village should not be in discard pre-cleanup; got {len(villages_in_discard)}"


def test_continue_skips_play_if_gain_was_intercepted():
    """If the gain landed somewhere unusual (trashed, exiled), Continue should
    not blindly append the card to in_play."""
    state, player = _new_state("Village")

    # Patch gain_card to drop the card on the floor (simulating a Watchtower
    # trash reaction) so the returned object lives in no normal zone.
    real_gain = state.gain_card
    intercepted: list = []

    def fake_gain(p, card, to_deck=False):
        intercepted.append(card)
        # Don't add to any zone — caller must handle this gracefully.
        return card

    state.gain_card = fake_gain  # type: ignore[assignment]

    # Should not raise, and Village should not appear in in_play (we skipped play).
    Continue().on_buy(state, player)
    assert not any(c.name == "Village" for c in player.in_play)
    state.gain_card = real_gain  # restore (not strictly needed, fresh state)
