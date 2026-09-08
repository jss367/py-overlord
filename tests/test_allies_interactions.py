"""Allies interactions with physical piles, turn timing, and shared play rules."""

from copy import deepcopy

import pytest

from dominion.cards.allies._rules import candidates, gain
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.test_allies_printed_rules import ProbeAI, SPLITS, cards, play, state


class ChoiceAI(ProbeAI):
    def __init__(self, decisions=None, modes=None):
        super().__init__()
        self.decisions = decisions or {}
        self.modes = modes

    def choose_allies_option(self, state, player, reason, options, default):
        choice = self.decisions.get(reason, default)
        return next((c for c in options if getattr(c, "name", None) == choice), choice)

    def choose_card_modes(
        self, state, player, card, options, minimum, maximum, defaults
    ):
        return self.modes(card, options) if self.modes else defaults


@pytest.mark.parametrize("pile", SPLITS, ids=lambda p: p[0])
def test_rotating_split_pile_preserves_counts_and_exposes_each_group(pile):
    s, p, _ = state()
    s.setup_supply([get_card(pile[0])])
    before = s.supply.copy()
    for expected in pile[1:] + pile[:1]:
        s.rotate_supply_pile(pile[0])
        assert s.top_supply_card(pile[0]) == expected
        assert [n for n in pile if get_card(n).may_be_gained(s)] == [expected]
        assert s.supply == before


def test_returned_split_card_rotates_only_contiguous_top_copies():
    s, p, _ = state()
    s.setup_supply([get_card("Town Crier")])
    gain(s, p, candidates(s, predicate=lambda c: c.name == "Town Crier"))
    returned = p.discard.pop()
    s.rotate_supply_pile("Town Crier")
    assert s.top_supply_card("Town Crier") == "Blacksmith"
    s._restore_to_supply_pile(returned)
    assert s.top_supply_card("Town Crier") == "Town Crier"
    s.rotate_supply_pile("Town Crier")
    assert s.top_supply_card("Town Crier") == "Blacksmith"
    assert s.supply["Town Crier"] == 4


@pytest.mark.parametrize(
    "top,next_card", [("Catapult", "Rocks"), ("Humble Castle", "Crumbling Castle")]
)
def test_battle_plan_rotates_other_expansions(top, next_card):
    s, p, _ = state()
    s.setup_supply([get_card(top)])
    p.ai = ChoiceAI({"rotate_pile": top})
    play(s, p, "Battle Plan")
    assert s.top_supply_card(top) == next_card
    assert get_card(next_card).may_be_gained(s)


def test_wizards_selects_ally_even_when_randomizer_names_lower_card():
    s = GameState(players=[])
    s.initialize_game([ProbeAI(), ProbeAI()], [get_card("Sorcerer")])
    assert len(s.allies) == 1
    assert all(p.favors == 1 for p in s.players)


def test_allies_gainer_uses_real_top_knight_and_updates_physical_pile():
    s, p, _ = state()
    s.supply = {"Knights": 2}
    s.pile_order = {"Knights": ["Sir Martin", "Dame Josephine"]}
    play(s, p, "Sunken Treasure")
    assert [c.name for c in p.discard] == ["Dame Josephine"]
    assert s.supply["Knights"] == 1
    assert s.pile_order["Knights"] == ["Sir Martin"]


def test_contract_repeated_play_preserves_both_actions_and_defers_new_duration():
    s, p, _ = state()
    p.hand = [get_card("Stronghold"), get_card("Village")]
    contract = play(s, p, "Contract")
    contract.on_play(s)
    assert len(contract.set_aside) == 2
    assert len(p.all_cards()) == 3
    p.deck = cards("Copper", 10)
    s.do_duration_phase()
    stronghold = next(c for c in p.in_play if c.name == "Stronghold")
    assert p.duration == [stronghold]
    assert len(p.hand) == 1  # Village only; Stronghold draws on the following turn.
    assert contract in p.in_play
    s.do_duration_phase()
    assert len(p.hand) == 4
    assert stronghold not in p.duration


def test_throne_room_and_importer_stay_until_delayed_gains_finish():
    s, p, _ = state()
    s.supply = {"Silver": 5}
    p.hand = [get_card("Importer")]
    throne = play(s, p, "Throne Room")
    importer = next(c for c in p.in_play if c.name == "Importer")
    p.deck = cards("Copper", 20)
    s.handle_cleanup_phase()
    assert throne in p.in_play and importer in p.in_play
    s.current_player_index = 0
    s.do_duration_phase()
    assert s.supply["Silver"] == 3
    assert throne in p.in_play and importer in p.in_play
    assert not p.duration
    s.handle_cleanup_phase()
    assert throne in p.discard and importer in p.discard


def test_highwayman_repeated_duration_discards_before_drawing_and_clears_attack():
    s, p, q = state()
    highwayman = play(s, p, "Highwayman")
    highwayman.on_play(s)
    assert q.highwayman_attacks == 2
    s.do_duration_phase()
    assert q.highwayman_attacks == 0
    assert p.hand == [highwayman]  # It was available to the first +3 Cards shuffle.
    assert highwayman not in p.in_play
    assert not p.duration
    assert len(p.all_cards()) == 1


@pytest.mark.parametrize(
    "name,resource", [("Galleria", "buys"), ("Guildmaster", "favors")]
)
def test_gain_trigger_counts_plays_survives_leaving_play_and_expires(name, resource):
    s, p, _ = state()
    card = play(s, p, name)
    card.on_play(s)
    p.in_play.remove(card)
    s.trash_card(p, card)
    before = getattr(p, resource)
    s.gain_card(p, get_card("Silver"))
    assert getattr(p, resource) == before + 2
    p.deck = cards("Copper", 10)
    s.handle_cleanup_phase()
    before = getattr(p, resource)
    s.gain_card(p, get_card("Silver"))
    assert getattr(p, resource) == before


@pytest.mark.parametrize("blocked_at_play", [False, True])
def test_skirmisher_protection_is_decided_when_played(blocked_at_play):
    s, p, q = state()
    q.hand = [get_card("Moat")] if blocked_at_play else []
    play(s, p, "Skirmisher")
    q.hand = cards("Copper", 4) + ([] if blocked_at_play else [get_card("Moat")])
    s.gain_card(p, get_card("Village"))
    assert len(q.hand) == (4 if blocked_at_play else 5)
    s.gain_card(p, get_card("Militia"))
    assert len(q.hand) == (4 if blocked_at_play else 3)


@pytest.mark.parametrize("ally", ["Order of Masons", "Order of Astrologers"])
def test_shuffle_allies_wait_for_actual_shuffle_and_preserve_ownership(ally):
    s, p, _ = state(ally)
    p.favors = 1
    p.deck = cards("Gold", 1)
    p.discard = cards("Curse", 2) + cards("Silver", 1)
    original = set(p.all_cards())
    s.allies[0].on_turn_start(s, p)
    assert p.favors == 1
    s.draw_cards(p, 1)
    assert p.favors == 1
    s.draw_cards(p, 1)
    assert p.favors == 0
    assert set(p.all_cards()) == original
    assert len(p.all_cards()) == 4


def test_astrologers_spends_before_selecting_and_honors_topdeck_order():
    s, p, _ = state("Order of Astrologers")
    p.favors = 2
    p.discard = [get_card("Gold"), get_card("Silver"), get_card("Copper")]
    events = []

    class AI(ChoiceAI):
        def choose_allies_option(self, state, player, reason, options, default):
            events.append((reason, player.favors))
            return super().choose_allies_option(state, player, reason, options, default)

    p.ai = AI()
    p.shuffle_discard_into_deck()
    assert events == [
        ("astrologers_favors", 2),
        ("astrologers_topdeck", 0),
        ("astrologers_topdeck", 0),
    ]
    assert [c.name for c in reversed(p.deck)] == ["Gold", "Silver", "Copper"]


def test_elder_count_can_decline_first_extra_and_take_second_extra():
    s, p, _ = state()
    s.supply = {"Copper": 5, "Duchy": 5}

    def modes(card, options):
        return ["copper"] if "copper" in options else ["duchy", "coins"]

    p.ai = ChoiceAI(modes=modes)
    p.hand = [get_card("Count")]
    play(s, p, "Elder")
    assert p.coins == 5
    assert [c.name for c in p.discard] == ["Copper", "Duchy"]


@pytest.mark.parametrize(
    "name,options,expected",
    [
        ("Pawn", ["coin", "card", "action"], (2, 3, 1)),
        ("Nobles", [True, False], (3, 2, 3)),
        ("Town", ["coins", "village"], (3, 4, 1)),
    ],
)
def test_elder_adds_choices_to_other_expansions(name, options, expected):
    s, p, _ = state()
    p.ai = ChoiceAI(modes=lambda card, offered: options)
    p.hand = [get_card(name)]
    p.deck = cards("Copper", 10)
    play(s, p, "Elder")
    assert (p.actions, p.coins, len(p.hand)) == expected


def test_elder_lurker_trashes_then_gains_same_card():
    s, p, _ = state()
    s.supply = {"Village": 1}
    p.ai = ChoiceAI(modes=lambda card, offered: ["gain", "trash"])
    p.hand = [get_card("Lurker")]
    play(s, p, "Elder")
    assert s.supply["Village"] == 0
    assert s.trash == []
    assert [c.name for c in p.discard] == ["Village"]
    assert p.cards_gained_this_turn == 1


def test_elder_catacombs_takes_looked_at_cards_then_draws_three_more():
    s, p, _ = state()
    p.hand = [get_card("Catacombs")]
    p.deck = cards("Copper", 6)
    play(s, p, "Elder")
    assert len(p.hand) == 6
    assert p.discard == []


def test_elder_choice_target_survives_simulation_copy_and_expires_at_cleanup():
    s, p, _ = state()
    p.hand = [get_card("Town")]
    play(s, p, "Elder")
    copied = deepcopy(s)
    cp = copied.current_player
    town = next(c for c in cp.in_play if c.name == "Town")
    before = (cp.actions, cp.coins)
    town.on_play(copied)
    assert (cp.actions, cp.coins) == (before[0] + 2, before[1] + 2)
    copied.handle_cleanup_phase()
    assert cp.elder_choices == {}


def test_lich_skips_two_turns_without_resolving_start_effects():
    s, p, q = state("Mountain Folk")
    p.favors = 5
    lich = play(s, p, "Lich")
    lich.on_play(s)
    p.hand = []
    p.deck = cards("Gold", 5)
    for expected in [1, 0]:
        s.current_player_index = 0
        s.phase = "start"
        s.handle_start_phase()
        assert s.current_player is q
        assert p.turns_to_skip == expected
        assert p.favors == 5
        assert p.hand == []
    assert p.turns_taken == 2


def test_island_folk_uses_normal_cleanup_hand_and_cannot_grant_third_turn():
    s, p, _ = state("Island Folk")
    p.favors = 10
    p.deck = cards("Copper", 20)
    s.handle_cleanup_phase()
    assert s.current_player is p
    assert len(p.hand) == 5
    assert p.favors == 5
    s.handle_start_phase()
    s.handle_cleanup_phase()
    assert s.current_player is not p
    assert p.favors == 5


@pytest.mark.parametrize("name", ["Merchant Camp", "Tent"])
@pytest.mark.parametrize("topdeck", [False, True])
def test_cleanup_topdeck_is_optional_and_happens_before_new_hand(name, topdeck):
    s, p, _ = state()
    p.ai = ChoiceAI({"topdeck_from_play": topdeck})
    card = play(s, p, name)
    p.deck = cards("Copper", 10)
    s.handle_cleanup_phase()
    assert (card in p.hand) is topdeck
    assert (card in p.discard) is not topdeck


def test_elder_treasurer_can_trash_and_gain_same_treasure_to_hand():
    s, p, _ = state()
    p.ai = ChoiceAI(modes=lambda card, offered: ["gain", "trash"])
    copper = get_card("Copper")
    p.hand = [get_card("Treasurer"), copper]
    play(s, p, "Elder")
    assert p.hand == [copper]
    assert s.trash == []
    assert p.cards_gained_this_turn == 1


def test_nested_throne_rooms_are_retained_with_multiplied_duration():
    s, p, _ = state()
    p.hand = [get_card("Throne Room"), get_card("Importer")]
    outer = play(s, p, "Throne Room")
    p.deck = cards("Copper", 10)
    s.handle_cleanup_phase()
    assert outer in p.in_play
    assert sorted(c.name for c in p.in_play) == [
        "Importer",
        "Throne Room",
        "Throne Room",
    ]


@pytest.mark.parametrize(
    "pile,family",
    zip(SPLITS, ["augur", "clash", "fort", "odyssey", "townsfolk", "wizard"]),
)
def test_each_split_card_has_its_printed_family_type(pile, family):
    for name in pile:
        assert family in {kind.value for kind in get_card(name).types}


def test_lich_consumes_skipped_fleet_turn_without_starting_another_normal_turn():
    s, p, q = state()
    p.turns_to_skip = 1
    s.fleet_extra_round_active = True
    s.fleet_extra_players = [p, q]
    s.handle_start_phase()
    assert s.fleet_extra_players == [q]
    assert s.current_player is q
    assert p.turns_taken == 1


def test_family_of_inventors_discount_follows_pile_after_rotation():
    s, p, _ = state("Family of Inventors")
    s.setup_supply([get_card("Town Crier")])
    p.ai = ChoiceAI({"family_of_inventors_pile": "Town Crier"})
    p.favors = 1
    s.allies[0].on_buy_phase_start(s, p)
    s.rotate_supply_pile("Town Crier")
    assert s.get_card_cost(p, get_card("Blacksmith")) == 2
    assert s.get_card_cost(p, get_card("Elder")) == 4


def test_swap_gain_to_hand_still_obeys_gatekeeper_exile():
    s, p, _ = state()
    s.supply = {"Village": 1, "Smithy": 1}
    p.hand = [get_card("Village")]
    p.gatekeeper_attacks = 1
    play(s, p, "Swap")
    assert p.hand == []
    assert [c.name for c in p.exile] == ["Smithy"]


@pytest.mark.parametrize(
    "gainer,ally", [("Hill Fort", None), ("Carpenter", "City-state")]
)
def test_gain_followup_does_not_retrieve_card_trashed_by_watchtower(gainer, ally):
    s, p, _ = state(ally)

    class AI(ChoiceAI):
        def choose_watchtower_reaction(self, state, player, card):
            return "trash"

    p.ai = AI()
    p.favors = 2
    p.hand = [get_card("Watchtower")]
    s.supply = {"Village": 1}
    play(s, p, gainer)
    assert [c.name for c in s.trash] == ["Village"]
    assert all(c.name != "Village" for c in p.all_cards())
    assert p.favors == 2


@pytest.mark.parametrize("hand_size,spend", [(0, 1), (2, 5)])
def test_peaceful_cult_can_spend_more_favors_than_cards_to_trash(hand_size, spend):
    s, p, _ = state("Peaceful Cult")
    p.ai = ChoiceAI({"peaceful_cult_favors": spend})
    p.hand = cards("Copper", hand_size)
    p.favors = spend
    s.allies[0].on_buy_phase_start(s, p)
    assert p.favors == 0
    assert p.hand == []
    assert len(s.trash) == hand_size
