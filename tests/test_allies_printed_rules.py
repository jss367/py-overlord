"""Printed rules regressions for the Allies expansion.

Run from the repository root with:
  python -m pytest -q tests/test_allies_printed_rules.py
Source: Rio Grande Games' November 2023 Allies rulebook, pages 3–11.
"""

import pytest

from dominion.allies.registry import get_ally
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


class ProbeAI(DummyAI):
    def choose_action(self, state, choices):
        return next((c for c in choices if c is not None), None)

    choose_treasure = choose_action
    choose_card_to_trash = choose_action

    def choose_buy(self, state, choices):
        return max(
            (c for c in choices if c is not None),
            key=lambda c: c.cost.coins,
            default=None,
        )

    def choose_cards_to_discard(self, state, player, choices, count, **kwargs):
        return choices[:count]

    def name_card_for_wishing_well(self, state, player):
        return "Estate"

    def should_spend_favor_on_cave_dwellers(self, state, player):
        return True


def state(ally=None):
    p, q = PlayerState(ProbeAI()), PlayerState(ProbeAI())
    s = GameState(players=[p, q], supply={})
    p.game_state = q.game_state = s
    s.log_callback = lambda *args: None
    s.phase = "action"
    if ally:
        s.allies = [get_ally(ally)]
    return s, p, q


def cards(name, n):
    return [get_card(name) for _ in range(n)]


def play(s, p, name):
    c = get_card(name)
    p.in_play.append(c)
    s.play_action_indirectly(p, c) if c.is_action else c.on_play(s)
    return c


STANDALONE = {
    "Barbarian": 5,
    "Bauble": 2,
    "Broker": 4,
    "Capital City": 5,
    "Carpenter": 4,
    "Contract": 5,
    "Courier": 4,
    "Emissary": 5,
    "Galleria": 5,
    "Guildmaster": 5,
    "Highwayman": 5,
    "Hunter": 5,
    "Importer": 3,
    "Innkeeper": 4,
    "Marquis": 6,
    "Merchant Camp": 3,
    "Modify": 5,
    "Royal Galley": 4,
    "Sentinel": 3,
    "Skirmisher": 5,
    "Specialist": 5,
    "Swap": 5,
    "Sycophant": 2,
    "Town": 4,
    "Underling": 3,
}
SPLITS = [
    ("Herb Gatherer", "Acolyte", "Sorceress", "Sibyl"),
    ("Battle Plan", "Archer", "Warlord", "Territory"),
    ("Tent", "Garrison", "Hill Fort", "Stronghold"),
    ("Old Map", "Voyage", "Sunken Treasure", "Distant Shore"),
    ("Town Crier", "Blacksmith", "Miller", "Elder"),
    ("Student", "Conjurer", "Sorcerer", "Lich"),
]
COSTS = dict(STANDALONE)
for pile in SPLITS:
    COSTS.update(
        {name: i + (2 if pile[0] == "Town Crier" else 3) for i, name in enumerate(pile)}
    )
LIAISONS = {
    "Bauble",
    "Broker",
    "Contract",
    "Emissary",
    "Guildmaster",
    "Importer",
    "Student",
    "Sycophant",
    "Underling",
}
DURATIONS = {
    "Contract",
    "Highwayman",
    "Importer",
    "Royal Galley",
    "Warlord",
    "Garrison",
    "Stronghold",
    "Voyage",
    "Conjurer",
}
TREASURES = {"Bauble", "Contract", "Sunken Treasure"}


@pytest.mark.parametrize("name", sorted(COSTS))
def test_printed_cost_and_key_types(name):
    c = get_card(name)
    assert (c.cost.coins, c.is_liaison, c.is_duration, c.is_treasure) == (
        COSTS[name],
        name in LIAISONS,
        name in DURATIONS,
        name in TREASURES,
    )


@pytest.mark.parametrize("pile", SPLITS, ids=lambda p: p[0])
def test_split_pile_has_four_copies_per_name_at_three_players(pile):
    s, p, q = state()
    s.players.append(PlayerState(ProbeAI()))
    assert get_card(pile[0]).starting_supply(s) == 4


@pytest.mark.parametrize("count", [1, 2, 3])
def test_sycophant_money_after_any_discard(count):
    s, p, _ = state()
    p.hand = cards("Estate", count)
    play(s, p, "Sycophant")
    assert p.coins == 3


def test_contract_favor():
    s, p, _ = state()
    play(s, p, "Contract")
    assert p.favors == 1


def test_courier_discards_estate_without_trashing_it():
    s, p, _ = state()
    p.deck = cards("Estate", 1)
    play(s, p, "Courier")
    assert s.trash == [] and len(p.discard) == 1


def test_barbarian_cannot_gain_buried_split_pile_card():
    s, p, q = state()
    q.deck = cards("Laboratory", 1)
    s.supply = {"Herb Gatherer": 4, "Acolyte": 4}
    play(s, p, "Barbarian")
    assert not any(c.name == "Acolyte" for c in q.discard)


def test_contract_accepts_duration_actions():
    s, p, _ = state()
    target = get_card("Caravan")
    p.hand = [target]
    c = play(s, p, "Contract")
    assert c._set_aside is target


@pytest.mark.parametrize("name", ["Contract", "Royal Galley"])
def test_set_aside_cards_remain_owned(name):
    s, p, _ = state()
    target = get_card("Great Hall")
    p.hand = [target]
    play(s, p, name)
    assert target in p.all_cards()


@pytest.mark.parametrize("name", ["Broker", "Importer", "Hill Fort"])
def test_mandatory_trash_or_gain_cannot_be_declined(name):
    s, p, _ = state()
    p.ai = DummyAI()
    p.hand = cards("Estate", 1)
    s.supply = {"Silver": 1}
    c = play(s, p, name)
    if name == "Importer":
        c.on_duration(s)
    if name == "Broker":
        assert any(c.name == "Estate" for c in s.trash)
    else:
        assert any(c.name == "Silver" for c in p.all_cards())


@pytest.mark.parametrize("name", ["Carpenter", "Importer"])
def test_gainers_use_discounted_cost(name):
    s, p, _ = state()
    p.cost_reduction = 1
    target = "Gold" if name == "Importer" else "Laboratory"
    s.supply = {target: 1}
    c = play(s, p, name)
    if name == "Importer":
        c.on_duration(s)
    assert any(c.name == target for c in p.all_cards())


@pytest.mark.parametrize("target,reduction", [("Gold", 0), ("Silver", 1)])
def test_galleria_only_rewards_current_cost_three_or_four(target, reduction):
    s, p, _ = state()
    play(s, p, "Galleria")
    p.cost_reduction = reduction
    before = p.buys
    s.gain_card(p, get_card(target))
    assert p.buys == before


def test_guildmaster_replays_stack_gain_rewards():
    s, p, _ = state()
    c = play(s, p, "Guildmaster")
    s.play_action_indirectly(p, c)
    s.gain_card(p, get_card("Copper"))
    assert p.favors == 2


def test_modify_can_cycle_with_empty_hand():
    s, p, _ = state()
    p.deck = cards("Copper", 2)
    before = p.actions
    play(s, p, "Modify")
    assert len(p.hand) == 1 and p.actions == before + 1


@pytest.mark.parametrize("target,remaining", [("Village", 5), ("Militia", 3)])
def test_skirmisher_trigger_and_discard_amount(target, remaining):
    s, p, q = state()
    q.hand = cards("Copper", 5)
    play(s, p, "Skirmisher")
    s.gain_card(p, get_card(target))
    assert len(q.hand) == remaining


def test_swap_gain_goes_to_hand():
    s, p, _ = state()
    p.hand = cards("Village", 1)
    s.supply = {"Village": 1, "Smithy": 1}
    play(s, p, "Swap")
    assert any(c.name == "Smithy" for c in p.hand)


def test_swap_does_not_gain_six_cost_card():
    s, p, _ = state()
    p.hand = cards("Laboratory", 1)
    s.supply = {"Laboratory": 1, "Lich": 1}
    play(s, p, "Swap")
    assert not any(c.name == "Lich" for c in p.all_cards())


def test_herb_gatherer_moves_deck_to_discard():
    s, p, _ = state()
    p.deck = cards("Estate", 2)
    p.discard = cards("Estate", 1)
    play(s, p, "Herb Gatherer")
    assert p.deck == [] and len(p.discard) == 3


def test_acolyte_external_trash_has_no_gain_trigger():
    s, p, _ = state()
    s.supply = {"Herb Gatherer": 4}
    s.trash_card(p, get_card("Acolyte"))
    assert p.discard == []


def test_battle_plan_reveal_draws_instead_of_gaining_attack():
    s, p, _ = state()
    p.hand = cards("Militia", 1)
    p.deck = cards("Copper", 3)
    s.supply = {"Militia": 5}
    play(s, p, "Battle Plan")
    assert s.supply["Militia"] == 5
    assert len(p.hand) == 3


def test_warlord_draw_is_delayed():
    s, p, _ = state()
    p.deck = cards("Copper", 5)
    play(s, p, "Warlord")
    assert p.hand == []


def test_garrison_printed_money():
    s, p, _ = state()
    play(s, p, "Garrison")
    assert p.coins == 2


def test_tent_stays_in_play_until_discarded():
    s, p, _ = state()
    c = play(s, p, "Tent")
    assert c in p.in_play and c not in p.deck


def test_stronghold_does_not_create_victory_tokens():
    s, p, _ = state()
    s.supply = {"Province": 1}
    play(s, p, "Stronghold")
    assert p.vp_tokens == 0


def test_stronghold_printed_victory_points():
    s, p, _ = state()
    assert get_card("Stronghold").get_victory_points(p) == 2


@pytest.mark.parametrize("when,estates", [("gain", 0), ("play", 1)])
def test_distant_shore_estate_timing(when, estates):
    s, p, _ = state()
    s.supply = {"Estate": 8}
    if when == "gain":
        s.gain_card(p, get_card("Distant Shore"))
    else:
        play(s, p, "Distant Shore")
    assert sum(c.name == "Estate" for c in p.all_cards()) == estates


@pytest.mark.parametrize("name", ["Sibyl", "Miller"])
def test_printed_action_bonus(name):
    s, p, _ = state()
    before = p.actions
    play(s, p, name)
    assert p.actions == before + 1


@pytest.mark.parametrize("target,expected", [("Estate", 0), ("Copper", 1)])
def test_student_only_conditional_favor(target, expected):
    s, p, _ = state()
    p.hand = cards(target, 1)
    play(s, p, "Student")
    assert p.favors == expected


def test_lich_does_not_discard_on_play():
    s, p, _ = state()
    p.deck = cards("Copper", 6)
    play(s, p, "Lich")
    assert len(p.hand) == 6


def test_lich_returns_to_discard_when_trashed():
    s, p, _ = state()
    c = get_card("Lich")
    s.trash_card(p, c)
    assert c in p.discard and c not in s.trash


def test_sorcerer_curse_goes_to_discard():
    s, p, q = state()
    s.supply = {"Curse": 5}
    q.deck = cards("Copper", 1)
    play(s, p, "Sorcerer")
    assert any(c.name == "Curse" for c in q.discard)


def test_highwayman_can_be_blocked_by_moat():
    s, p, q = state()
    q.hand = cards("Moat", 1)
    play(s, p, "Highwayman")
    assert q.highwayman_attacks == 0


def test_highwayman_discards_itself_before_duration_draw():
    s, p, _ = state()
    c = play(s, p, "Highwayman")
    c.on_duration(s)
    assert c in p.hand and c not in p.in_play


def test_architects_guild_triggers_on_non_victory_gain():
    s, p, _ = state("Architects' Guild")
    p.favors = 2
    s.supply = {"Smithy": 1}
    s.gain_card(p, get_card("Gold"))
    assert any(c.name == "Smithy" for c in p.discard)


def test_band_of_nomads_respects_cost_discount():
    s, p, _ = state("Band of Nomads")
    p.favors = 1
    p.cost_reduction = 1
    s.gain_card(p, get_card("Silver"))
    assert p.favors == 1


def test_cave_dwellers_can_draw_with_empty_hand():
    s, p, _ = state("Cave Dwellers")
    p.favors = 1
    p.deck = cards("Gold", 1)
    s.allies[0].on_turn_start(s, p)
    assert len(p.hand) == 1


def test_circle_of_witches_triggers_on_liaison():
    s, p, q = state("Circle of Witches")
    p.favors = 2
    s.supply = {"Curse": 5}
    q.hand = cards("Moat", 1)
    play(s, p, "Underling")
    assert any(c.name == "Curse" for c in q.discard)


def test_city_state_plays_newly_gained_action():
    s, p, _ = state("City-state")
    p.favors = 2
    c = s.gain_card(p, get_card("Village"))
    assert c in p.in_play


def test_crafters_guild_topdecks_gain():
    s, p, _ = state("Crafters' Guild")
    p.favors = 2
    s.supply = {"Smithy": 1}
    s.allies[0].on_turn_start(s, p)
    assert any(c.name == "Smithy" for c in p.deck)


def test_family_of_inventors_triggers_before_buys():
    s, p, _ = state("Family of Inventors")
    p.favors = 1
    s.supply = {"Smithy": 1}
    s._handle_start_of_buy_phase_effects()
    assert s.get_card_cost(p, get_card("Smithy")) == 3


def test_fellowship_of_scribes_ignores_plain_treasures():
    s, p, _ = state("Fellowship of Scribes")
    p.favors = 1
    p.deck = cards("Gold", 1)
    s.fire_ally_play_hooks(p, get_card("Copper"))
    assert p.favors == 1 and p.hand == []


@pytest.mark.parametrize("size", [3, 5, 7])
def test_gang_of_pickpockets_discards_to_four(size):
    s, p, _ = state("Gang of Pickpockets")
    p.hand = cards("Copper", size)
    s.allies[0].on_turn_start(s, p)
    assert len(p.hand) == min(size, 4)


def test_island_folk_keeps_normal_hand_size():
    s, p, _ = state("Island Folk")
    p.favors = 5
    p.deck = cards("Copper", 10)
    s.handle_cleanup_phase()
    assert len(p.hand) == 5


def test_league_of_bankers_money_is_available_before_buys():
    s, p, _ = state("League of Bankers")
    p.favors = 8
    s._handle_start_of_buy_phase_effects()
    assert p.coins == 2 and p.coin_tokens == 0


@pytest.mark.parametrize(
    "favors,coins,actions,buys", [(3, 0, 0, 0), (5, 1, 0, 0), (10, 1, 1, 1)]
)
def test_league_of_shopkeepers_printed_thresholds(favors, coins, actions, buys):
    s, p, _ = state("League of Shopkeepers")
    p.favors = favors
    p.actions = p.buys = 0
    s.fire_ally_play_hooks(p, get_card("Underling"))
    assert (p.favors, p.coins, p.actions, p.buys) == (favors, coins, actions, buys)


def test_market_towns_respects_voyage_limit():
    s, p, _ = state("Market Towns")
    p.favors = 1
    p.hand = cards("Village", 1)
    p.voyage_cards_from_hand_remaining = 0
    s._handle_start_of_buy_phase_effects()
    assert len(p.hand) == 1 and p.favors == 1


def test_order_of_astrologers_does_not_spend_without_shuffle():
    s, p, _ = state("Order of Astrologers")
    p.favors = 1
    p.deck = cards("Copper", 4)
    p.discard = cards("Gold", 1)
    s.allies[0].on_turn_start(s, p)
    assert p.favors == 1


def test_order_of_masons_does_not_buy_extra_cleanup_draw():
    s, p, _ = state("Order of Masons")
    p.favors = 2
    p.deck = cards("Copper", 10)
    s.handle_cleanup_phase()
    assert len(p.hand) == 5 and p.favors == 2


def test_peaceful_cult_trashes_at_start_of_buy_phase():
    s, p, _ = state("Peaceful Cult")
    p.favors = 1
    p.hand = cards("Estate", 1)
    s._handle_start_of_buy_phase_effects()
    assert len(s.trash) == 1


def test_plateau_shepherds_scores_two_per_pair():
    s, p, _ = state("Plateau Shepherds")
    p.favors = 3
    p.deck = cards("Estate", 3)
    assert s.allies[0].score_bonus(s, p) == 6


def test_woodworkers_guild_has_no_gain_cost_cap():
    s, p, _ = state("Woodworkers' Guild")
    p.favors = 1
    p.hand = cards("Village", 1)
    s.supply = {"King's Court": 1}
    s._handle_start_of_buy_phase_effects()
    assert any(c.name == "King's Court" for c in p.all_cards())
