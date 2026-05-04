"""Tests for the newly implemented Dominion Base Set cards (and Moat reaction)."""

from __future__ import annotations

from typing import Optional

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import ChooseFirstActionAI, DummyAI


def _make_state(num_players: int = 1, ai_class=ChooseFirstActionAI) -> GameState:
    players = [PlayerState(ai_class()) for _ in range(num_players)]
    state = GameState(players=players)
    # Use the full supply so cards that gain (Bandit, Bureaucrat, Feast,
    # Artisan) can find their gains.
    state.setup_supply([])
    for p in players:
        p.hand = []
        p.deck = []
        p.discard = []
        p.in_play = []
        p.duration = []
    return state


def play_action(state: GameState, player: PlayerState, card: Card) -> None:
    if card in player.hand:
        player.hand.remove(card)
    player.in_play.append(card)
    card.on_play(state)


# ---- Cellar -----------------------------------------------------------------


def test_cellar_gives_action_and_redraws_discarded():
    state = _make_state()
    player = state.players[0]

    cellar = get_card("Cellar")
    junk_estate = get_card("Estate")
    player.hand = [cellar, junk_estate, get_card("Copper"), get_card("Silver")]
    # Stack the deck with predictable cards so we can verify draw count.
    player.deck = [get_card("Gold"), get_card("Gold"), get_card("Gold")]

    actions_before = player.actions

    play_action(state, player, cellar)

    assert player.actions == actions_before + 1
    # Estate should have been discarded as junk.
    assert any(c.name == "Estate" for c in player.discard)
    # And we should have drawn at least one card to replace it.
    assert any(c.name == "Gold" for c in player.hand)


# ---- Merchant + Silver bonus ------------------------------------------------


def test_merchant_first_silver_gives_bonus_coin():
    state = _make_state()
    player = state.players[0]

    merchant = get_card("Merchant")
    silver = get_card("Silver")

    player.hand = [merchant, silver]
    play_action(state, player, merchant)

    # Merchant draws 1 card and gives +1 Action; bonus is queued.
    assert player.merchant_silver_bonus >= 1

    # Now play the Silver: should get +$2 from Silver + $1 Merchant bonus.
    coins_before = player.coins
    silver.on_play(state)

    # Silver's on_play applied its base stats (+$2) AND fired play_effect
    # which adds the Merchant bonus (+$1).
    assert player.coins - coins_before == 3
    assert player.merchant_silver_bonus_used


def test_merchant_only_first_silver_gets_bonus():
    state = _make_state()
    player = state.players[0]

    merchant = get_card("Merchant")
    s1 = get_card("Silver")
    s2 = get_card("Silver")
    player.hand = [merchant, s1, s2]
    play_action(state, player, merchant)

    coins_before = player.coins
    s1.on_play(state)
    s2.on_play(state)

    # First Silver: +$2 + $1 bonus = +$3. Second Silver: +$2. Total +$5.
    assert player.coins - coins_before == 5


def test_merchant_does_not_apply_to_silver_played_after_an_earlier_silver():
    """A Silver played before any Merchant must consume the "first Silver"
    slot, so that a later Silver played after a Merchant gets no bonus.
    """

    state = _make_state()
    player = state.players[0]

    s1 = get_card("Silver")
    merchant = get_card("Merchant")
    s2 = get_card("Silver")
    player.hand = [s1, merchant, s2]

    coins_before = player.coins

    # Play Silver before any Merchant (e.g. via Storyteller / Black Market /
    # Vassal-style effects in a normal turn).
    s1.on_play(state)
    # Now play Merchant (queues +$1 bonus).
    play_action(state, player, merchant)
    # Now play a second Silver.
    s2.on_play(state)

    # First Silver: +$2 (no Merchant active yet, no bonus).
    # Merchant: +0 coins directly.
    # Second Silver: +$2 only -- the "first Silver this turn" was already
    # played, so the +$1 bonus must NOT apply.
    assert player.coins - coins_before == 4


# ---- Vassal -----------------------------------------------------------------


def test_vassal_discards_top_when_not_action():
    state = _make_state()
    player = state.players[0]

    vassal = get_card("Vassal")
    player.hand = [vassal]
    player.deck = [get_card("Copper")]

    play_action(state, player, vassal)

    assert player.coins >= 2
    assert any(c.name == "Copper" for c in player.discard)


def test_vassal_plays_top_action():
    class PlayActionAI(ChooseFirstActionAI):
        def should_play_vassal_action(self, state, player, card):
            return True

    state = _make_state(ai_class=PlayActionAI)
    player = state.players[0]

    vassal = get_card("Vassal")
    smithy = get_card("Smithy")
    player.hand = [vassal]
    player.deck = [get_card("Copper"), get_card("Copper"), get_card("Copper"), smithy]

    play_action(state, player, vassal)

    # Smithy is played: should draw 3 cards.
    drawn = [c for c in player.hand if c.name == "Copper"]
    assert len(drawn) == 3
    assert smithy in player.in_play


# ---- Bureaucrat -------------------------------------------------------------


def test_bureaucrat_gains_silver_on_deck_and_topdecks_victory():
    state = _make_state(num_players=2)
    attacker, defender = state.players

    bureaucrat = get_card("Bureaucrat")
    attacker.hand = [bureaucrat]
    defender.hand = [
        get_card("Copper"),
        get_card("Copper"),
        get_card("Estate"),
    ]

    play_action(state, attacker, bureaucrat)

    # Attacker has Silver on top of deck.
    assert attacker.deck and attacker.deck[-1].name == "Silver"
    # Defender's Estate is now on top of their deck.
    assert defender.deck and defender.deck[-1].name == "Estate"
    assert all(c.name != "Estate" for c in defender.hand)


def test_bureaucrat_no_victory_in_hand_reveals_only():
    state = _make_state(num_players=2)
    attacker, defender = state.players

    bureaucrat = get_card("Bureaucrat")
    attacker.hand = [bureaucrat]
    defender.hand = [get_card("Copper"), get_card("Silver")]
    defender.deck = []

    play_action(state, attacker, bureaucrat)

    # No topdeck — defender's hand unchanged size.
    assert len(defender.hand) == 2
    # Defender's deck stays empty (no topdeck happened).
    assert defender.deck == []


# ---- Moneylender ------------------------------------------------------------


def test_moneylender_trashes_copper_for_three_coins():
    state = _make_state()
    player = state.players[0]

    moneylender = get_card("Moneylender")
    player.hand = [moneylender, get_card("Copper")]
    state.trash = []

    play_action(state, player, moneylender)

    assert any(c.name == "Copper" for c in state.trash)
    assert player.coins == 3


def test_moneylender_does_nothing_without_copper():
    state = _make_state()
    player = state.players[0]

    moneylender = get_card("Moneylender")
    player.hand = [moneylender, get_card("Silver")]

    play_action(state, player, moneylender)

    assert player.coins == 0


# ---- Poacher ----------------------------------------------------------------


def test_poacher_basic_no_empty_piles():
    state = _make_state()
    player = state.players[0]

    poacher = get_card("Poacher")
    player.hand = [poacher, get_card("Copper"), get_card("Copper")]
    player.deck = [get_card("Estate")]

    play_action(state, player, poacher)

    assert player.coins == 1
    assert player.actions >= 1
    # No empty piles → no discards required.
    assert len(player.hand) == 3  # 2 Coppers + drawn Estate


def test_poacher_discards_per_empty_pile():
    state = _make_state()
    player = state.players[0]

    # Empty two supply piles to force two discards.
    state.supply["Curse"] = 0
    state.supply["Estate"] = 0

    poacher = get_card("Poacher")
    player.hand = [
        poacher,
        get_card("Copper"),
        get_card("Copper"),
        get_card("Copper"),
    ]
    player.deck = [get_card("Silver")]

    play_action(state, player, poacher)

    # +1 Card draws Silver into hand (4 in hand). Then must discard 2.
    assert len(player.hand) == 2
    assert len(player.discard) == 2


# ---- Bandit -----------------------------------------------------------------


def test_bandit_gains_gold_and_trashes_top_treasure():
    state = _make_state(num_players=2)
    attacker, defender = state.players

    bandit = get_card("Bandit")
    attacker.hand = [bandit]
    defender.deck = [
        get_card("Copper"),
        get_card("Silver"),
    ]

    play_action(state, attacker, bandit)

    assert any(c.name == "Gold" for c in attacker.discard)
    # Silver was trashed (it's a non-Copper Treasure, top of revealed pair).
    assert any(c.name == "Silver" for c in state.trash)
    # The other revealed card (Copper) should be discarded.
    assert any(c.name == "Copper" for c in defender.discard)


def test_bandit_no_treasures_just_discards():
    state = _make_state(num_players=2)
    attacker, defender = state.players

    bandit = get_card("Bandit")
    attacker.hand = [bandit]
    defender.deck = [get_card("Estate"), get_card("Estate")]

    play_action(state, attacker, bandit)

    # Nothing trashed; both Estates discarded.
    assert all(c.name != "Estate" for c in state.trash)
    assert sum(1 for c in defender.discard if c.name == "Estate") == 2


# ---- Artisan ----------------------------------------------------------------


def test_artisan_gains_to_hand_and_topdecks_from_hand():
    state = _make_state()
    player = state.players[0]

    artisan = get_card("Artisan")
    junk = get_card("Estate")
    player.hand = [artisan, junk]

    play_action(state, player, artisan)

    # Player should have gained a $5 card to hand (default: highest-cost
    # action under $5 — likely something gainable from supply). And a card
    # from hand should be on top of deck.
    assert player.deck, "expected something topdecked"
    # Hand should now contain the gained card (we've also topdecked one of
    # them, so net hand size = 2 + 1 gained - 1 topdecked = 2).
    assert len(player.hand) == 2 or len(player.hand) == 1


def test_artisan_does_not_resurrect_card_trashed_by_watchtower():
    """If Watchtower trashes Artisan's gain, the card must NOT also end up
    in hand. The trashed instance must remain only in the trash pile.
    """

    class WatchtowerTrashAI(ChooseFirstActionAI):
        def choose_watchtower_reaction(self, state, player, gained_card):
            # Trash everything that Artisan tries to gain.
            return "trash"

    state = _make_state(ai_class=WatchtowerTrashAI)
    player = state.players[0]

    artisan = get_card("Artisan")
    watchtower = get_card("Watchtower")
    junk = get_card("Estate")
    player.hand = [artisan, watchtower, junk]

    play_action(state, player, artisan)

    # The gained card should be in the trash, NOT duplicated in hand.
    assert len(state.trash) >= 1, "expected the gained card to be trashed"
    trashed = state.trash[-1]
    assert trashed not in player.hand
    assert trashed not in player.discard
    assert trashed not in player.deck

    # The same Card object must not appear simultaneously in trash and in any
    # of the player's zones.
    all_player_cards = (
        player.hand + player.discard + player.deck + player.in_play
    )
    for trashed_card in state.trash:
        assert trashed_card not in all_player_cards, (
            f"trashed {trashed_card.name} also present in player zones"
        )


# ---- Chancellor (1E) --------------------------------------------------------


def test_chancellor_optionally_discards_deck():
    class DiscardingAI(ChooseFirstActionAI):
        def should_chancellor_discard_deck(self, state, player):
            return True

    state = _make_state(ai_class=DiscardingAI)
    player = state.players[0]

    chancellor = get_card("Chancellor")
    player.hand = [chancellor]
    player.deck = [get_card("Copper") for _ in range(7)]

    play_action(state, player, chancellor)

    assert player.coins == 2
    assert len(player.deck) == 0
    assert len(player.discard) == 7


def test_chancellor_can_skip_discarding():
    class SkipAI(ChooseFirstActionAI):
        def should_chancellor_discard_deck(self, state, player):
            return False

    state = _make_state(ai_class=SkipAI)
    player = state.players[0]

    chancellor = get_card("Chancellor")
    player.hand = [chancellor]
    player.deck = [get_card("Copper") for _ in range(7)]

    play_action(state, player, chancellor)

    assert player.coins == 2
    assert len(player.deck) == 7
    assert len(player.discard) == 0


# ---- Feast (1E) -------------------------------------------------------------


def test_feast_trashes_self_and_gains_card():
    state = _make_state()
    player = state.players[0]

    feast = get_card("Feast")
    player.hand = [feast]

    play_action(state, player, feast)

    # Feast itself trashed.
    assert feast in state.trash
    assert feast not in player.in_play
    # Some card costing up to $5 has been gained.
    assert player.discard, "Expected Feast to gain a card"
    gained = player.discard[-1]
    assert gained.cost.coins <= 5


# ---- Spy (1E) ---------------------------------------------------------------


def test_spy_self_can_keep_top():
    class KeepingAI(ChooseFirstActionAI):
        def choose_topdeck_or_discard(self, state, chooser, target, revealed, *, is_self):
            return False  # always topdeck

    state = _make_state(ai_class=KeepingAI)
    player = state.players[0]

    spy = get_card("Spy")
    player.hand = [spy]
    player.deck = [get_card("Estate"), get_card("Gold")]

    play_action(state, player, spy)

    # Self deck still has the Estate left after we drew Gold for +1 Card.
    assert any(c.name == "Estate" for c in player.deck)


def test_spy_attacks_opponent_can_force_discard():
    class DiscardOpponent(ChooseFirstActionAI):
        def choose_topdeck_or_discard(self, state, chooser, target, revealed, *, is_self):
            return not is_self  # discard from opponent, keep own

    state = _make_state(num_players=2, ai_class=DiscardOpponent)
    attacker, defender = state.players

    spy = get_card("Spy")
    attacker.hand = [spy]
    attacker.deck = [get_card("Copper")]  # for the +1 Card
    defender.deck = [get_card("Gold")]

    play_action(state, attacker, spy)

    # Opponent's revealed Gold gets discarded.
    assert any(c.name == "Gold" for c in defender.discard)


# ---- Thief (1E) -------------------------------------------------------------


def test_thief_trashes_treasure_and_gains_it():
    class GainAllAI(ChooseFirstActionAI):
        def should_gain_thief_treasure(self, state, player, card):
            return True

    state = _make_state(num_players=2, ai_class=GainAllAI)
    attacker, defender = state.players

    thief = get_card("Thief")
    attacker.hand = [thief]
    defender.deck = [get_card("Estate"), get_card("Silver")]

    play_action(state, attacker, thief)

    # Silver should be trashed-then-gained → in attacker's discard.
    assert any(c.name == "Silver" for c in attacker.discard)
    # Estate (non-treasure) discarded by defender.
    assert any(c.name == "Estate" for c in defender.discard)


def test_thief_no_treasures_does_nothing():
    state = _make_state(num_players=2)
    attacker, defender = state.players

    thief = get_card("Thief")
    attacker.hand = [thief]
    defender.deck = [get_card("Estate"), get_card("Estate")]

    play_action(state, attacker, thief)

    assert sum(1 for c in defender.discard if c.name == "Estate") == 2
    assert all(not c.is_treasure for c in state.trash)


# ---- Woodcutter -------------------------------------------------------------


def test_woodcutter_grants_buy_and_two_coins():
    state = _make_state()
    player = state.players[0]
    player.buys = 1
    player.coins = 0

    woodcutter = get_card("Woodcutter")
    player.hand = [woodcutter]

    play_action(state, player, woodcutter)

    assert player.buys == 2
    assert player.coins == 2


# ---- Moat reaction ----------------------------------------------------------


def test_moat_blocks_attack_via_react_to_attack():
    state = _make_state(num_players=2)
    attacker, defender = state.players

    militia = get_card("Militia")
    attacker.hand = [militia]
    defender.hand = [
        get_card("Moat"),
        get_card("Copper"),
        get_card("Copper"),
        get_card("Copper"),
        get_card("Estate"),
    ]

    play_action(state, attacker, militia)

    # Defender should not have been forced to discard anything.
    assert len(defender.hand) == 5
    assert any(c.name == "Moat" for c in defender.hand)


def test_moat_reaction_returns_true_for_blocked_attack():
    state = _make_state(num_players=2)
    attacker, defender = state.players
    moat = get_card("Moat")
    defender.hand = [moat]

    blocked = moat.react_to_attack(state, defender, attacker, get_card("Witch"))
    assert blocked is True


def test_default_card_react_to_attack_is_noop():
    state = _make_state()
    player = state.players[0]
    smithy = get_card("Smithy")
    assert smithy.react_to_attack(state, player, player, get_card("Witch")) is False
