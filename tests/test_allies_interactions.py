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


def test_elder_catacombs_discards_the_same_cards_it_put_into_hand():
    s, p, _ = state()
    p.hand = [get_card("Catacombs")]
    p.deck = cards("Gold", 3) + cards("Copper", 3)
    play(s, p, "Elder")
    assert [c.name for c in p.hand] == ["Gold"] * 3
    assert [c.name for c in p.discard] == ["Copper"] * 3


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


@pytest.mark.parametrize("name", ["Importer", "Contract"])
def test_trashed_duration_resolves_without_restoring_ownership(name):
    from dominion.events.adventures_events import Bonfire

    s, p, _ = state()
    s.supply = {"Silver": 5}
    p.hand = [get_card("Village")] if name == "Contract" else []
    duration = play(s, p, name)
    p.ai.choose_cards_to_trash = lambda state, choices, count: choices[:count]
    Bonfire().on_buy(s, p)
    assert duration in s.trash
    assert duration not in p.all_cards()
    if name == "Contract":
        assert any(c.name == "Village" for c in p.all_cards())
    p.deck = cards("Copper", 20)
    s.do_duration_phase()
    if name == "Importer":
        assert s.supply["Silver"] == 4
    else:
        assert any(c.name == "Village" for c in p.in_play)
    assert duration not in p.in_play
    s.handle_cleanup_phase()
    assert duration not in p.all_cards()
    assert s.trash.count(duration) == 1


def test_completed_multiplier_does_not_follow_old_duration_on_a_later_turn():
    s, p, _ = state()
    importer = get_card("Importer")
    p.hand = [importer]
    throne = play(s, p, "Throne Room")
    p.deck = cards("Copper", 30)
    s.handle_cleanup_phase()
    s.current_player_index = 0
    s.do_duration_phase()
    s.handle_cleanup_phase()
    assert throne in p.discard and importer in p.discard
    s.current_player_index = 0
    p.discard.remove(throne)
    p.discard.remove(importer)
    p.in_play.append(importer)
    s.play_action_indirectly(p, importer)
    p.in_play.append(throne)
    p.hand = [get_card("Village")]
    s.play_action_indirectly(p, throne)
    s.handle_cleanup_phase()
    assert importer in p.in_play
    assert throne in p.discard
    assert throne not in p.in_play


def test_rotated_pile_keeps_cheap_and_player_tokens():
    from dominion.traits import apply_trait

    s, p, _ = state()
    s.setup_supply([get_card("Town Crier")])
    apply_trait(s, "Cheap", "Town Crier")
    s.add_pile_token(p, "Town Crier", "+$1")
    s.add_pile_token(p, "Town Crier", "-$2 cost")
    s.rotate_supply_pile("Town Crier")
    blacksmith = get_card("Blacksmith")
    assert s.get_card_cost(p, blacksmith) == 0
    assert s.has_pile_token(p, "Blacksmith", "+$1")
    before = p.coins
    play(s, p, "Blacksmith")
    assert p.coins == before + 1
    s.move_player_token(p, "+$1", "Elder")
    assert s.player_token_pile(p, "+$1") == "Town Crier"
    s.remove_pile_token(p, "Blacksmith", "+$1")
    assert not s.has_pile_token(p, "Town Crier", "+$1")


def test_rotated_reckless_treasure_plays_twice():
    from dominion.traits import apply_trait

    s, p, _ = state()
    s.setup_supply([get_card("Old Map"), get_card("Village")])
    apply_trait(s, "Reckless", "Old Map")
    s.rotate_supply_pile("Old Map")
    s.rotate_supply_pile("Old Map")
    assert s.top_supply_card("Old Map") == "Sunken Treasure"
    treasure = get_card("Sunken Treasure")
    p.in_play.append(treasure)
    s.play_treasure_indirectly(p, treasure)
    assert [c.name for c in p.discard] == ["Village", "Village"]


@pytest.mark.parametrize(
    "trait,loot", [("Cursed", "Doubloons"), ("Cursed", "Hammer"), ("Rich", None), ("Hasty", None)]
)
def test_rotated_pile_gain_traits(trait, loot, monkeypatch):
    from dominion.traits import apply_trait

    s, p, _ = state()
    s.setup_supply([get_card("Town Crier")])
    apply_trait(s, trait, "Town Crier")
    s.rotate_supply_pile("Town Crier")
    gained = s.take_top_supply_card("Town Crier")
    if loot is not None:
        monkeypatch.setattr("random.choice", lambda choices: loot)
    s.gain_card(p, gained)
    assert gained.name == "Blacksmith"
    if trait == "Cursed":
        assert any(c.name == "Curse" for c in p.discard)
        expected = ["Blacksmith", loot, "Curse"]
        if loot == "Doubloons":
            expected.append("Gold")
        assert sorted(c.name for c in p.discard) == sorted(expected)
    elif trait == "Rich":
        assert [c.name for c in p.discard] == ["Blacksmith", "Silver"]
    else:
        assert gained in s.hasty_set_aside[id(p)]
        assert gained not in p.discard


@pytest.mark.parametrize("empty_original", [False, True])
def test_fawning_gains_exposed_card_even_when_original_group_is_empty(empty_original):
    from dominion.traits import apply_trait

    s, p, _ = state()
    s.setup_supply([get_card("Town Crier")])
    apply_trait(s, "Fawning", "Town Crier")
    if empty_original:
        s.supply["Town Crier"] = 0
    else:
        s.rotate_supply_pile("Town Crier")
    s.gain_card(p, get_card("Province"))
    assert [c.name for c in p.discard] == ["Province", "Blacksmith"]
    assert s.supply["Town Crier"] == (0 if empty_original else 4)
    assert s.supply["Blacksmith"] == 3


@pytest.mark.parametrize("trait", ["Patient", "Tireless", "Shy", "Fated"])
def test_rotated_pile_traits_follow_cards_through_player_zones(trait):
    from dominion.traits import apply_trait

    s, p, _ = state()
    s.setup_supply([get_card("Town Crier")])
    apply_trait(s, trait, "Blacksmith")  # Registration also uses physical keys.
    s.rotate_supply_pile("Town Crier")
    blacksmith = get_card("Blacksmith")
    p.deck = cards("Copper", 20)
    if trait == "Patient":
        p.hand = [blacksmith]
        s.handle_cleanup_phase()
        assert blacksmith in s.patient_mat[id(p)]
    elif trait == "Tireless":
        p.in_play = [blacksmith]
        s.handle_cleanup_phase()
        assert blacksmith in p.deck
        assert blacksmith not in p.discard
    elif trait == "Shy":
        p.hand = [blacksmith]
        s._handle_shy_start_of_turn(p)
        assert blacksmith in p.discard
        assert len(p.hand) == 2
    else:
        p.deck = []
        p.discard = [blacksmith] + cards("Copper", 10)
        p.shuffle_discard_into_deck()
        assert p.deck[-1] is blacksmith


@pytest.mark.parametrize("trait", ["Friendly", "Pious", "Inherited"])
def test_trait_pile_effects_take_the_current_top_card(trait):
    from dominion.traits import apply_trait

    s, p, _ = state()
    s.setup_supply([get_card("Town Crier")])
    s.rotate_supply_pile("Town Crier")
    p.deck = [get_card("Estate")]
    apply_trait(s, trait, "Town Crier")
    if trait == "Friendly":
        s.discard_card(p, get_card("Town Crier"))
        assert [c.name for c in p.discard] == ["Town Crier", "Blacksmith"]
    elif trait == "Pious":
        s.trash_card(p, get_card("Copper"))
        assert [c.name for c in s.trash] == ["Copper", "Blacksmith"]
    else:
        assert [c.name for c in p.deck] == ["Blacksmith"]
    assert s.supply["Town Crier"] == 4
    assert s.supply["Blacksmith"] == 3


def test_elder_allows_an_extra_option_in_each_of_counts_two_clauses():
    s, p, _ = state()
    s.supply = {"Copper": 5, "Duchy": 5}
    p.ai = ChoiceAI(modes=lambda card, options: (
        ["discard", "copper"] if "copper" in options else ["coins", "duchy"]
    ))
    p.hand = [get_card("Count")] + cards("Copper", 2)
    play(s, p, "Elder")
    assert p.hand == []
    assert [c.name for c in p.discard] == ["Copper", "Copper", "Copper", "Duchy"]
    assert p.coins == 5


def test_elder_pirate_ship_resolves_printed_coin_option_before_attack():
    # Seaside rulebook: coins are the first option, attack is the second.
    s, p, q = state()
    p.ai = ChoiceAI(modes=lambda card, options: ["attack", "coins"])
    p.hand = [get_card("Pirate Ship")]
    q.deck = cards("Silver", 2)
    play(s, p, "Elder")
    assert p.coins == 2  # Elder's $2; Pirate Ship had no tokens at its coin step.
    assert p.pirate_ship_tokens == 1
    assert [c.name for c in s.trash] == ["Silver"]


def test_buying_rotated_pile_applies_embargo_and_tax_tokens():
    s, p, _ = state()
    s.setup_supply([get_card("Town Crier")])
    s.embargo_tokens["Town Crier"] = 1
    s.tax_tokens["Town Crier"] = 2
    s.rotate_supply_pile("Town Crier")
    p.coins = 3
    s._commit_buy(p, get_card("Blacksmith"))
    assert p.debt == 2
    assert s.tax_tokens["Town Crier"] == 0
    assert s.embargo_tokens["Town Crier"] == 1
    assert sorted(c.name for c in p.discard) == ["Blacksmith", "Curse"]
    assert s.supply["Town Crier"] == 4
    assert s.supply["Blacksmith"] == 3


def test_legacy_token_placement_uses_physical_pile_key():
    from dominion.events.empires_events import Tax

    s, p, _ = state()
    s.supply = {name: 4 for name in SPLITS[4]}
    s.rotate_supply_pile("Town Crier")
    p.ai.choose_pile_to_embargo = lambda state, player: "Blacksmith"
    play(s, p, "Embargo")
    Tax().on_buy(s, p)  # Its highest-cost choice is Elder from the same pile.
    assert s.embargo_tokens == {"Town Crier": 1}
    assert s.tax_tokens == {"Town Crier": 1}


def test_tax_setup_places_one_token_per_physical_split_pile():
    from dominion.events.empires_events import Tax

    s = GameState(players=[])
    s.log_callback = lambda *args: None
    s.initialize_game([ProbeAI(), ProbeAI()], [get_card("Town Crier")], events=[Tax()])
    assert s.tax_tokens["Town Crier"] == 1
    assert all(name not in s.tax_tokens for name in SPLITS[4][1:])


def test_trade_route_uses_randomizer_type_and_single_token_for_rotated_castles():
    s, p, _ = state()
    s.setup_supply([get_card("Trade Route"), get_card("Humble Castle"), get_card("Battle Plan")])
    assert s.trade_route_tokens_on_piles["Humble Castle"] is True
    assert "Crumbling Castle" not in s.trade_route_tokens_on_piles
    assert "Territory" not in s.trade_route_tokens_on_piles
    assert "Battle Plan" not in s.trade_route_tokens_on_piles
    s.rotate_supply_pile("Humble Castle")
    s.gain_card(p, s.take_top_supply_card("Humble Castle"))
    assert s.trade_route_mat_tokens == 1
    assert s.trade_route_tokens_on_piles["Humble Castle"] is False
    s.gain_card(p, s.take_top_supply_card("Humble Castle"))
    assert s.trade_route_mat_tokens == 1


def test_training_event_bonuses_sunken_treasure_from_the_odyssey_pile():
    from dominion.events.training import Training

    s, p, _ = state()
    s.supply = {name: 4 for name in SPLITS[3]}
    Training().on_buy(s, p)
    assert s.player_token_pile(p, "+$1") == "Old Map"
    s.rotate_supply_pile("Old Map")
    s.rotate_supply_pile("Old Map")
    treasure = s.take_top_supply_card("Old Map")
    p.in_play.append(treasure)
    s.play_treasure_indirectly(p, treasure)
    assert p.coins == 1


def test_duration_gained_from_trash_has_one_owner_but_keeps_original_effect():
    s, p, q = state()
    s.supply = {"Silver": 5}
    importer = play(s, p, "Importer")
    p.in_play.remove(importer)
    s.trash_card(p, importer)
    s.trash.remove(importer)
    s.gain_card(q, importer, from_supply=False)
    assert importer not in p.all_cards()
    assert importer in q.all_cards()
    s.do_duration_phase()
    assert [c.name for c in p.discard] == ["Silver"]
    assert q.discard == [importer]
    assert importer not in p.in_play


@pytest.mark.parametrize("force_spend", [False, True])
def test_desert_guides_preserves_favors_by_default_when_no_cards_exist(force_spend):
    s, p, _ = state("Desert Guides")
    p.favors = 3
    if force_spend:
        p.ai = ChoiceAI({"desert_guides_redraw": True})
    s.allies[0].on_turn_start(s, p)
    assert p.favors == (0 if force_spend else 3)
    assert p.hand == []


@pytest.mark.parametrize("now", [False, True])
def test_elder_does_not_add_an_option_to_barges_either_timing_choice(now):
    s, p, _ = state()
    p.ai = ChoiceAI(modes=lambda card, options: [True, False])
    p.ai.should_resolve_barge_now = lambda state, player: now
    barge = get_card("Barge")
    p.hand = [barge]
    p.deck = cards("Copper", 10)
    play(s, p, "Elder")
    assert len(p.hand) == (3 if now else 0)
    assert p.buys == (2 if now else 1)
    assert (barge in p.duration) is not now
    if not now:
        s.do_duration_phase()
        assert len(p.hand) == 3
        assert p.buys == 2


def test_elder_can_select_counts_printed_gain_modes_even_with_empty_piles():
    s, p, _ = state()
    s.supply = {"Copper": 0, "Duchy": 0}
    p.ai = ChoiceAI(modes=lambda card, options: (
        ["copper"] if "copper" in options else ["duchy"]
    ))
    p.hand = [get_card("Count"), get_card("Estate")]
    play(s, p, "Elder")
    assert [c.name for c in p.hand] == ["Estate"]
    assert p.discard == []
    assert p.coins == 2


@pytest.mark.parametrize("extra_names", [["Underling"], ["Miller", "Elder"]])
def test_rotated_inspiring_plays_use_ways_tokens_allies_and_nested_triggers(extra_names):
    from dominion.traits import apply_trait
    from dominion.ways.sheep import WayOfTheSheep

    s, p, _ = state()
    s.setup_supply([get_card("Town Crier"), get_card("Underling")])
    apply_trait(s, "Inspiring", "Town Crier")
    s.rotate_supply_pile("Town Crier")
    blacksmith = get_card("Blacksmith")
    p.in_play = [blacksmith]
    p.hand = [get_card(name) for name in extra_names]
    s.ways = [WayOfTheSheep()]
    p.ai.choose_way = lambda state, card, options: options[0]
    s.add_pile_token(p, extra_names[0], "+$1")
    played = []

    class Observer:
        def on_play_card(self, state, player, card):
            played.append(card.name)

    s.allies = [Observer()]
    s._maybe_inspiring_extra_play(p, blacksmith)
    assert played == extra_names
    assert p.actions_played == len(extra_names)
    assert p.coins == 3 * len(extra_names)
    assert p.favors == 0  # Underling used a Way instead of its printed text.
    assert p.hand == []


@pytest.mark.parametrize("spend", [False, True])
def test_fellowship_of_scribes_favor_spend_is_optional(spend):
    s, p, _ = state("Fellowship of Scribes")
    p.ai = ChoiceAI({"fellowship_of_scribes": spend})
    p.favors = 1
    p.deck = cards("Copper", 5)
    play(s, p, "Village")
    assert p.favors == (0 if spend else 1)
    assert len(p.hand) == (2 if spend else 1)


@pytest.mark.parametrize("name", ["Importer", "Crew"])
@pytest.mark.parametrize("way_name", ["Way of the Horse", "Way of the Butterfly"])
def test_returned_pending_duration_stays_in_supply_and_releases_multiplier(name, way_name):
    from dominion.ways.registry import get_way

    s, p, _ = state()
    s.setup_supply([get_card(name), get_card("Smithy")])
    initial_count = s.supply[name]
    s.supply[name] -= 1
    duration = get_card(name)
    p.hand = [duration]
    p.deck = cards("Copper", 30)
    way = get_way(way_name)
    s.ways = [way]
    plays = 0

    def choose_way(state, card, choices):
        nonlocal plays
        if card is duration:
            plays += 1
            return way if plays == 2 else None
        return None

    p.ai.choose_way = choose_way
    throne = play(s, p, "Throne Room")
    assert duration not in p.all_cards()
    assert s.supply[name] == initial_count
    s.handle_cleanup_phase()
    assert throne in p.discard and throne not in p.in_play
    s.current_player_index = 0
    gains_before = p.cards_gained_this_turn
    s.do_duration_phase()
    assert p.cards_gained_this_turn == gains_before + (1 if name == "Importer" else 0)
    assert duration not in p.all_cards()
    assert duration not in p.in_play
    assert s.supply[name] == initial_count
    assert not p.duration


@pytest.mark.parametrize("name", ["Taskmaster", "Samurai", "Hireling"])
@pytest.mark.parametrize("trashed", [False, True])
def test_repeated_persistent_durations_keep_every_pending_instruction(name, trashed):
    s, p, _ = state()
    duration = get_card(name)
    p.hand = [duration]
    p.deck = cards("Copper", 30)
    play(s, p, "Throne Room")
    assert p.duration.count(duration) == 2
    if trashed:
        p.in_play.remove(duration)
        s.trash_card(p, duration)
    for _ in range(3):
        p.gained_five_last_turn = True
        before = len(p.hand) if name == "Hireling" else p.coins
        if name == "Hireling":
            s.handle_start_phase()
            assert len(p.hand) == before + 2
        else:
            s.do_duration_phase()
            assert p.coins == before + 2
        assert p.duration.count(duration) == 2
        assert (duration in p.all_cards()) is not trashed


def test_family_of_inventors_tokens_are_cumulative_global_and_persistent():
    s, p, q = state("Family of Inventors")
    s.setup_supply([get_card("Town Crier")])
    p.ai = ChoiceAI({"family_of_inventors_pile": "Town Crier"})
    p.favors = 2
    ally = s.allies[0]
    ally.on_buy_phase_start(s, p)
    for player in [p, q]:
        assert s.get_card_cost(player, get_card("Town Crier")) == 1
    p.deck = cards("Copper", 10)
    s.handle_cleanup_phase()
    assert s.get_card_cost(q, get_card("Town Crier")) == 1
    s.current_player_index = 0
    ally.on_buy_phase_start(s, p)
    s.rotate_supply_pile("Town Crier")
    for player in [p, q]:
        assert s.get_card_cost(player, get_card("Town Crier")) == 0
        assert s.get_card_cost(player, get_card("Blacksmith")) == 1


def test_repeated_archive_releases_all_renewals_when_its_set_aside_cards_run_out():
    s, p, _ = state()
    archive = get_card("Archive")
    p.hand = [archive]
    p.deck = cards("Copper", 30)
    throne = play(s, p, "Throne Room")
    assert archive.set_aside
    assert p.duration.count(archive) == 2
    for _ in range(3):
        if not archive.set_aside:
            break
        s.do_duration_phase()
    assert archive.set_aside == []
    assert p.duration == []
    s.handle_cleanup_phase()
    assert archive in p.discard and throne in p.discard


@pytest.mark.parametrize("kind", ["Townsfolk", "Knights", "Ruins"])
def test_ambassador_only_gains_exposed_copies_for_each_opponent(kind):
    from dominion.game.player_state import PlayerState

    s, p, q = state()
    r = PlayerState(ProbeAI())
    r.game_state = s
    s.players.append(r)
    if kind == "Townsfolk":
        s.setup_supply([get_card("Town Crier")])
        returned = s.take_top_supply_card("Town Crier")
        s.rotate_supply_pile("Town Crier")
        pile, next_card = "Town Crier", "Blacksmith"
        count_before_return = s.supply[pile]
    else:
        name, next_card = (
            ("Dame Josephine", "Sir Martin") if kind == "Knights"
            else ("Ruined Library", "Ruined Village")
        )
        pile = kind
        s.supply = {pile: 1}
        s.pile_order = {pile: [next_card]}
        returned = get_card(name)
        count_before_return = 1
    p.hand = [returned]
    play(s, p, "Ambassador")
    assert [c.name for c in q.discard] == [returned.name]
    assert r.discard == []
    assert p.hand == []
    assert s.top_supply_card(pile) == next_card
    assert s.supply[pile] == count_before_return
    assert returned not in p.all_cards()


def test_ambassador_does_not_return_or_gain_non_supply_horses():
    s, p, q = state()
    s.supply = {"Horse": 10}
    s.non_supply_pile_names = {"Horse"}
    horse = get_card("Horse")
    p.hand = [horse]
    play(s, p, "Ambassador")
    assert p.hand == [horse]
    assert q.discard == []
    assert s.supply["Horse"] == 10


@pytest.mark.parametrize("trait", ["Hasty", "Patient"])
@pytest.mark.parametrize("copied", [False, True])
def test_trait_set_aside_cards_remain_owned_and_scored_in_copied_games(trait, copied):
    from dominion.traits import apply_trait

    s, p, _ = state()
    s.setup_supply([get_card("Old Map")])
    apply_trait(s, trait, "Old Map")
    for _ in range(3):
        s.rotate_supply_pile("Old Map")
    shore = s.take_top_supply_card("Old Map")
    s.gain_card(p, shore)
    if trait == "Patient":
        p.discard.remove(shore)
        p.hand.append(shore)
        p.deck = cards("Copper", 10)
        s.handle_cleanup_phase()
    if copied:
        s = deepcopy(s)
        p = s.players[0]
    assert sum(c.name == "Distant Shore" for c in p.all_cards()) == 1
    assert p.get_victory_points() == 2
    assert all(c.name != "Distant Shore" for c in p.hand + p.deck + p.discard)


@pytest.mark.parametrize("destination", ["discard", "hand", "deck"])
@pytest.mark.parametrize("city_first", [False, True])
def test_city_state_and_hasty_gain_triggers_can_resolve_in_either_order(destination, city_first):
    from dominion.traits import apply_trait

    s, p, _ = state("City-state")
    s.setup_supply([get_card("Town Crier")])
    apply_trait(s, "Hasty", "Town Crier")
    s.rotate_supply_pile("Town Crier")
    p.ai = ChoiceAI({"city_state_before_gain_effects": city_first})
    p.favors = 2
    p.deck = cards("Copper", 10)
    blacksmith = s.take_top_supply_card("Town Crier")
    s.gain_card(p, blacksmith, to_hand=destination == "hand", to_deck=destination == "deck")
    assert p.favors == (0 if city_first else 2)
    assert (blacksmith in p.in_play) is city_first
    assert (blacksmith in s.hasty_set_aside.get(id(p), [])) is not city_first
    assert p.all_cards().count(blacksmith) == 1
    assert len(p.hand) == (6 if city_first else 0)


def test_declining_city_state_before_gain_effects_does_not_offer_it_twice():
    from dominion.traits import apply_trait

    class DeclineAI(ChoiceAI):
        offers = 0

        def choose_allies_option(self, state, player, reason, options, default):
            if reason == "city_state":
                self.offers += 1
                return False
            return super().choose_allies_option(state, player, reason, options, default)

    s, p, _ = state("City-state")
    s.setup_supply([get_card("Village")])
    apply_trait(s, "Hasty", "Village")
    p.ai = DeclineAI()
    p.favors = 2
    village = s.take_top_supply_card("Village")
    s.gain_card(p, village)
    assert p.ai.offers == 1
    assert p.favors == 2
    assert village in s.hasty_set_aside[id(p)]
    assert village not in p.in_play


@pytest.mark.parametrize("off_turn,favors", [(True, 2), (False, 1)])
def test_hasty_gain_does_not_bypass_city_state_eligibility(off_turn, favors):
    from dominion.traits import apply_trait

    s, p, q = state("City-state")
    s.setup_supply([get_card("Village")])
    apply_trait(s, "Hasty", "Village")
    owner = q if off_turn else p
    owner.favors = favors
    village = s.take_top_supply_card("Village")
    s.gain_card(owner, village)
    assert owner.favors == favors
    assert village in s.hasty_set_aside[id(owner)]
    assert village not in owner.in_play


@pytest.mark.parametrize("method", ["Hasty City-state", "Innovation"])
def test_played_garrison_does_not_count_its_own_gain(method):
    from dominion.traits import apply_trait

    s, p, _ = state("City-state" if method == "Hasty City-state" else None)
    s.setup_supply([get_card("Tent")])
    if method == "Hasty City-state":
        apply_trait(s, "Hasty", "Tent")
    else:
        from dominion.projects.innovation import Innovation

        p.projects = [Innovation()]
    s.rotate_supply_pile("Tent")
    p.favors = 2
    garrison = s.take_top_supply_card("Tent")
    s.gain_card(p, garrison)
    assert garrison in p.in_play
    assert garrison.tokens == 0
    silver = s.take_top_supply_card("Silver")
    s.gain_card(p, silver)
    assert garrison.tokens == 1


@pytest.mark.parametrize("way_name", [None, "Way of the Horse", "Way of the Butterfly"])
def test_sunken_treasure_only_excludes_durations_physically_in_play(way_name):
    from dominion.ways.registry import get_way

    s, p, _ = state()
    s.setup_supply([get_card("Importer")])
    importer = s.take_top_supply_card("Importer")
    p.hand = [importer]
    p.deck = cards("Copper", 10)
    plays = 0
    if way_name:
        way = get_way(way_name)
        s.ways = [way]

        def choose_way(state, card, choices):
            nonlocal plays
            if card is importer:
                plays += 1
                return way if plays == 2 else None
            return None

        p.ai.choose_way = choose_way
    play(s, p, "Throne Room")
    assert importer in p.duration
    assert (importer in p.in_play) is (way_name is None)
    before = s.supply["Importer"]
    play(s, p, "Sunken Treasure")
    if way_name:
        assert [c.name for c in p.discard] == ["Importer"]
        assert p.discard[0] is not importer
        assert s.supply["Importer"] == before - 1
    else:
        assert p.discard == []
        assert s.supply["Importer"] == before


@pytest.mark.parametrize("return_order", [
    ("Blacksmith", "Town Crier"), ("Town Crier", "Blacksmith")
])
def test_consecutive_way_of_the_horse_returns_preserve_mixed_pile_order(return_order):
    from dominion.ways.registry import get_way

    s, p, _ = state()
    s.setup_supply([get_card("Town Crier")])
    held = {"Town Crier": s.take_top_supply_card("Town Crier")}
    s.rotate_supply_pile("Town Crier")
    held["Blacksmith"] = s.take_top_supply_card("Town Crier")
    before = s.supply.copy()
    way = get_way("Way of the Horse")
    s.ways = [way]
    p.ai.choose_way = lambda state, card, choices: way
    p.hand = list(held.values())
    p.deck = cards("Copper", 10)
    for name in return_order:
        s.play_action_from_hand_indirectly(p, held[name])
    assert s.top_supply_card("Town Crier") == return_order[-1]
    assert all(s.supply[n] == before[n] + 1 for n in return_order)
    assert s.take_top_supply_card("Town Crier").name == return_order[-1]
    assert s.take_top_supply_card("Town Crier").name == return_order[0]
    assert all(s.supply[n] == before[n] for n in return_order)
    assert all(c not in p.all_cards() for c in held.values())


@pytest.mark.parametrize("members", [
    ("Town Crier", "Blacksmith"), ("Catapult", "Rocks")
])
@pytest.mark.parametrize("reverse", [False, True])
def test_split_pile_return_sequence_survives_copy_and_rotation(members, reverse):
    s, p, _ = state()
    s.setup_supply([get_card(members[0])])
    first = s.take_top_supply_card(members[0])
    s.rotate_supply_pile(members[0])
    second = s.take_top_supply_card(members[0])
    returned = [second, first] if reverse else [first, second]
    for card in returned:
        s._restore_to_supply_pile(card)
    s = deepcopy(s)
    assert s.top_supply_card(members[0]) == returned[-1].name
    s.rotate_supply_pile(members[0])
    assert s.top_supply_card(members[0]) == returned[0].name
