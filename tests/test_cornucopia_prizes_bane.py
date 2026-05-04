"""Tests for Cornucopia 1E Tournament Prizes and Young Witch Bane mechanic."""

from typing import Optional

from dominion.cards.base_card import Card
from dominion.cards.cornucopia.prizes import PRIZE_CARD_NAMES
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI, DummyAI


# ---------------------------------------------------------------------------
# Helpers / AIs
# ---------------------------------------------------------------------------


class FirstChoiceAI(ChooseFirstActionAI):
    """Plays first action, picks first non-None for buys/discards/etc."""

    def choose_buy(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_card_to_trash(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_treasure(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None


class TournamentReveals(FirstChoiceAI):
    """Reveals Tournament Provinces, picks first available Prize."""

    def __init__(self, prize_name: Optional[str] = None):
        super().__init__()
        self.prize_name = prize_name

    def should_reveal_tournament_province(self, state, player):
        return True

    def choose_tournament_prize(self, state, player, choices):
        if self.prize_name is not None:
            for c in choices:
                if c.name == self.prize_name:
                    return c
        return choices[0] if choices else None


class TournamentNoReveal(FirstChoiceAI):
    def should_reveal_tournament_province(self, state, player):
        return False


class SilversTrustySteedAI(FirstChoiceAI):
    def choose_trusty_steed_options(self, state, player, options):
        return ["coins", "silvers"]


class RevealBaneAI(DummyAI):
    @property
    def name(self) -> str:
        return "BaneRevealer"

    def should_reveal_bane(self, state, player):
        return True


class NoRevealBaneAI(DummyAI):
    @property
    def name(self) -> str:
        return "NoBaneReveal"

    def should_reveal_bane(self, state, player):
        return False


def _setup(ai, kingdom_cards):
    state = GameState(players=[])
    state.initialize_game([ai], kingdom_cards)
    player = state.players[0]
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    player.actions = 1
    player.buys = 1
    player.coins = 0
    return state, player


def _setup_two(ai_a, ai_b, kingdom_cards):
    state = GameState(players=[])
    state.initialize_game([ai_a, ai_b], kingdom_cards)
    for p in state.players:
        p.hand = []
        p.deck = []
        p.discard = []
        p.in_play = []
        p.actions = 1
        p.buys = 1
        p.coins = 0
    return state, state.players[0], state.players[1]


# ---------------------------------------------------------------------------
# Setup / supply
# ---------------------------------------------------------------------------


def test_tournament_kingdom_adds_prize_pile():
    state, _ = _setup(FirstChoiceAI(), [get_card("Tournament")])
    for name in PRIZE_CARD_NAMES:
        assert state.supply.get(name) == 1, f"{name} should have one copy in Prize pile"


def test_prizes_are_not_buyable():
    state, _ = _setup(FirstChoiceAI(), [get_card("Tournament")])
    for name in PRIZE_CARD_NAMES:
        prize = get_card(name)
        assert not prize.may_be_bought(state)


# ---------------------------------------------------------------------------
# Tournament behaviour
# ---------------------------------------------------------------------------


def test_tournament_reveal_province_gains_prize_topdeck():
    ai = TournamentReveals(prize_name="Bag of Gold")
    state, player = _setup(ai, [get_card("Tournament")])
    tourn = get_card("Tournament")
    province = get_card("Province")
    player.hand = [tourn, province]
    player.deck = []
    player.actions = 1

    player.hand.remove(tourn)
    player.in_play.append(tourn)
    tourn.on_play(state)

    # Tournament gives +1 Action (we started with 1 → now 2).
    assert player.actions == 2
    # Province should have been discarded.
    assert all(c.name != "Province" for c in player.hand)
    assert any(c.name == "Province" for c in player.discard)
    # Top of deck should be the chosen Prize (Bag of Gold).
    assert player.deck and player.deck[0].name == "Bag of Gold"
    # Prize pile decremented.
    assert state.supply["Bag of Gold"] == 0


def test_tournament_no_reveal_path_grants_card_and_coin():
    ai = TournamentNoReveal()
    state, player = _setup(ai, [get_card("Tournament")])
    tourn = get_card("Tournament")
    filler = get_card("Copper")
    player.hand = [tourn]
    player.deck = [filler]
    player.coins = 0
    player.actions = 1

    player.hand.remove(tourn)
    player.in_play.append(tourn)
    tourn.on_play(state)

    # +1 Card → drew the Copper into hand.
    assert any(c.name == "Copper" for c in player.hand)
    # +$1
    assert player.coins == 1


def test_tournament_can_choose_duchy_when_prizes_gone():
    ai = TournamentReveals()
    state, player = _setup(ai, [get_card("Tournament")])
    # Empty all Prize piles.
    for name in PRIZE_CARD_NAMES:
        state.supply[name] = 0

    tourn = get_card("Tournament")
    province = get_card("Province")
    player.hand = [tourn, province]
    duchy_count_before = state.supply["Duchy"]

    player.hand.remove(tourn)
    player.in_play.append(tourn)
    tourn.on_play(state)

    # Duchy was the only option → topdecked.
    assert player.deck and player.deck[0].name == "Duchy"
    assert state.supply["Duchy"] == duchy_count_before - 1


# ---------------------------------------------------------------------------
# Individual Prize behaviours
# ---------------------------------------------------------------------------


def test_bag_of_gold_gains_gold_on_top_of_deck():
    ai = FirstChoiceAI()
    state, player = _setup(ai, [get_card("Tournament")])
    bag = get_card("Bag of Gold")
    player.hand = [bag]
    player.actions = 1
    gold_before = state.supply["Gold"]

    player.hand.remove(bag)
    player.in_play.append(bag)
    bag.on_play(state)

    assert player.actions == 2  # +1 Action
    assert state.supply["Gold"] == gold_before - 1
    assert player.deck and player.deck[0].name == "Gold"


def test_diadem_grants_coin_per_unused_action():
    ai = FirstChoiceAI()
    state, player = _setup(ai, [get_card("Tournament")])
    diadem = get_card("Diadem")
    player.hand = [diadem]
    player.coins = 0
    # Force 3 unused actions at the time Diadem is played.
    player.actions = 3

    player.hand.remove(diadem)
    player.in_play.append(diadem)
    diadem.on_play(state)

    # $2 base + $1 per unused Action = $5
    assert player.coins == 2 + 3


def test_followers_full_attack_resolution():
    attacker_ai = FirstChoiceAI()
    target_ai = FirstChoiceAI()
    state, atk, target = _setup_two(
        attacker_ai, target_ai, [get_card("Tournament")]
    )

    followers = get_card("Followers")
    atk.hand = [followers]
    atk.deck = [get_card("Copper") for _ in range(5)]  # ensure cards to draw

    # Target has 5 cards in hand → must discard down to 3.
    target.hand = [
        get_card("Estate"), get_card("Estate"),
        get_card("Copper"), get_card("Copper"),
        get_card("Silver"),
    ]

    estate_before = state.supply["Estate"]
    curse_before = state.supply["Curse"]

    atk.hand.remove(followers)
    atk.in_play.append(followers)
    followers.on_play(state)

    # +2 Cards drawn for attacker.
    assert len(atk.hand) == 2
    # Attacker gained an Estate.
    assert any(c.name == "Estate" for c in atk.discard + atk.deck)
    assert state.supply["Estate"] == estate_before - 1
    # Target gained a Curse.
    assert any(c.name == "Curse" for c in target.discard + target.deck + target.hand)
    assert state.supply["Curse"] == curse_before - 1
    # Target hand now contains 3 cards.
    assert len(target.hand) == 3


def test_princess_reduces_card_costs_by_two():
    ai = FirstChoiceAI()
    state, player = _setup(ai, [get_card("Tournament"), get_card("Smithy")])
    princess = get_card("Princess")
    player.hand = [princess]
    player.buys = 0

    # Pre-play: a Smithy costs $4.
    smithy = get_card("Smithy")
    assert state.get_card_cost(player, smithy) == 4

    player.hand.remove(princess)
    player.in_play.append(princess)
    princess.on_play(state)

    # +1 Buy
    assert player.buys == 1
    # Cost reduced by $2 (Smithy → $2).
    assert state.get_card_cost(player, smithy) == 2
    # And cost cannot drop below 0 — Copper still costs $0.
    assert state.get_card_cost(player, get_card("Copper")) == 0


def test_trusty_steed_default_two_cards_two_actions():
    ai = FirstChoiceAI()
    state, player = _setup(ai, [get_card("Tournament")])
    steed = get_card("Trusty Steed")
    player.hand = [steed]
    player.deck = [get_card("Copper") for _ in range(3)]
    player.actions = 1

    player.hand.remove(steed)
    player.in_play.append(steed)
    steed.on_play(state)

    # +2 Cards
    assert len(player.hand) == 2
    # +2 Actions on top of starting 1
    assert player.actions == 3


def test_trusty_steed_silvers_then_dump_deck():
    ai = SilversTrustySteedAI()
    state, player = _setup(ai, [get_card("Tournament")])
    steed = get_card("Trusty Steed")
    player.hand = [steed]
    player.deck = [get_card("Copper"), get_card("Copper")]
    player.coins = 0
    player.actions = 1
    silver_before = state.supply["Silver"]

    player.hand.remove(steed)
    player.in_play.append(steed)
    steed.on_play(state)

    # +$2 from "coins" pick.
    assert player.coins == 2
    # 4 Silvers gained.
    assert state.supply["Silver"] == silver_before - 4
    silvers_in_discard = sum(1 for c in player.discard if c.name == "Silver")
    assert silvers_in_discard == 4
    # Deck dumped into discard → deck empty, discard contains the Coppers too.
    assert player.deck == []
    assert sum(1 for c in player.discard if c.name == "Copper") == 2


# ---------------------------------------------------------------------------
# Young Witch / Bane
# ---------------------------------------------------------------------------


def test_young_witch_bane_setup_picks_existing_kingdom_pile():
    state, _ = _setup(
        FirstChoiceAI(),
        [get_card("Young Witch"), get_card("Village"), get_card("Smithy")],
    )
    # Village costs $3 — eligible. Smithy costs $4 — not eligible.
    assert state.bane_card_name == "Village"
    assert state.supply.get("Village", 0) > 0


def test_young_witch_bane_setup_adds_extra_pile_when_none_eligible():
    # Choose a kingdom of cards that all cost more than $3.
    kingdom = [
        get_card("Young Witch"),
        get_card("Smithy"),    # $4
        get_card("Market"),    # $5
        get_card("Festival"),  # $5
        get_card("Laboratory"),  # $5
    ]
    state, _ = _setup(FirstChoiceAI(), kingdom)
    bane = state.bane_card_name
    assert bane != ""
    bane_card = get_card(bane)
    assert bane_card.cost.coins in (2, 3)
    assert state.supply.get(bane, 0) > 0


def test_young_witch_blocked_by_bane_in_hand():
    state, atk, target = _setup_two(
        FirstChoiceAI(),
        RevealBaneAI(),
        [get_card("Young Witch"), get_card("Village"), get_card("Smithy")],
    )
    assert state.bane_card_name == "Village"

    yw = get_card("Young Witch")
    atk.hand = [yw, get_card("Copper"), get_card("Copper")]
    atk.deck = [get_card("Copper") for _ in range(5)]
    target.hand = [get_card("Village"), get_card("Copper"), get_card("Copper")]
    curse_before = state.supply["Curse"]

    atk.hand.remove(yw)
    atk.in_play.append(yw)
    yw.on_play(state)

    # Target should NOT have gained a Curse.
    assert state.supply["Curse"] == curse_before
    assert all(c.name != "Curse" for c in target.hand + target.deck + target.discard)


def test_young_witch_curses_target_without_bane():
    state, atk, target = _setup_two(
        FirstChoiceAI(),
        RevealBaneAI(),
        [get_card("Young Witch"), get_card("Village"), get_card("Smithy")],
    )
    assert state.bane_card_name == "Village"

    yw = get_card("Young Witch")
    atk.hand = [yw, get_card("Copper"), get_card("Copper")]
    atk.deck = [get_card("Copper") for _ in range(5)]
    # No Village in target's hand → no Bane.
    target.hand = [get_card("Estate"), get_card("Copper"), get_card("Copper")]
    curse_before = state.supply["Curse"]

    atk.hand.remove(yw)
    atk.in_play.append(yw)
    yw.on_play(state)

    assert state.supply["Curse"] == curse_before - 1
    assert any(c.name == "Curse" for c in target.discard + target.deck + target.hand)


def test_young_witch_no_bane_reveal_when_ai_declines():
    state, atk, target = _setup_two(
        FirstChoiceAI(),
        NoRevealBaneAI(),
        [get_card("Young Witch"), get_card("Village"), get_card("Smithy")],
    )
    assert state.bane_card_name == "Village"

    yw = get_card("Young Witch")
    atk.hand = [yw, get_card("Copper"), get_card("Copper")]
    atk.deck = [get_card("Copper") for _ in range(5)]
    target.hand = [get_card("Village"), get_card("Copper"), get_card("Copper")]
    curse_before = state.supply["Curse"]

    atk.hand.remove(yw)
    atk.in_play.append(yw)
    yw.on_play(state)

    # Target has Bane but didn't reveal → still cursed.
    assert state.supply["Curse"] == curse_before - 1


def test_bane_does_not_block_other_attacks():
    """Bane only blocks Young Witch, not (e.g.) Witch."""
    state, atk, target = _setup_two(
        FirstChoiceAI(),
        RevealBaneAI(),
        [get_card("Young Witch"), get_card("Village"), get_card("Smithy")],
    )
    assert state.bane_card_name == "Village"

    witch = get_card("Witch")
    atk.hand = [witch]
    target.hand = [get_card("Village"), get_card("Copper")]
    curse_before = state.supply["Curse"]

    atk.hand.remove(witch)
    atk.in_play.append(witch)
    witch.on_play(state)

    # Witch does not check the Bane → curse goes through.
    assert state.supply["Curse"] == curse_before - 1
