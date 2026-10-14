"""Real engine paths for the remaining named decision-hook gaps in #344."""

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.base_card import Card, CardCost, CardStats, CardType
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.projects.capitalism import Capitalism
from dominion.prophecies import get_prophecy
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def make_state(strategy=None, kingdom=(), players=2):
    strategies = [strategy or EnhancedStrategy()] + [EnhancedStrategy() for _ in range(players - 1)]
    state = GameState([])
    state.log_callback = lambda *_: None
    state.initialize_game([GeneticAI(s) for s in strategies], [get_card(n) for n in kingdom])
    state.phase = "action"
    for player in state.players:
        player.hand, player.deck, player.discard, player.in_play, player.duration = [], [], [], [], []
        player.actions = player.coins = 0
    return state, state.players[0]


def test_courtier_forwards_the_physical_reveal_and_bonus_choices():
    class Policy(EnhancedStrategy):
        def choose_courtier_reveal(self, state, player, choices):
            self.offered = choices
            return choices[0]  # Deliberately reveal fewer types than the default.

        def choose_courtier_options(self, state, player, choices, count):
            assert count == 1
            return ["buy"]

    strategy = Policy()
    state, player = make_state(strategy, ("Courtier", "Minion"))
    copper, minion = get_card("Copper"), get_card("Minion")
    player.hand = [copper, minion]
    get_card("Courtier").play_effect(state)
    assert strategy.offered == [copper, minion]
    assert player.hand == [copper, minion]
    assert (player.buys, player.coins, player.discard) == (2, 0, [])


@pytest.mark.parametrize("modifier,name,count", [
    ("Charlatan", "Curse", 2), ("Capitalism", "Militia", 3),
    ("Enlightenment", "Silver", 2), ("Inheritance", "Estate", 3),
    ("Inheritance and Capitalism", "Estate", 3),
])
def test_courtier_counts_live_types_once(modifier, name, count):
    class Policy(EnhancedStrategy):
        def choose_courtier_options(self, state, player, options, num_choices):
            self.count = num_choices
            return ["coins", "gold", "buy"][:num_choices]

    strategy = Policy()
    state, player = make_state(strategy, ("Courtier",))
    if modifier == "Charlatan":
        state.supply["Charlatan"] = 10
    elif modifier == "Enlightenment":
        state.prophecy = get_prophecy("Enlightenment")
        state.prophecy.is_active = True
    else:
        if "Capitalism" in modifier:
            player.projects = [Capitalism()]
        if "Inheritance" in modifier:
            player.inherited_action_name = "Militia" if "Capitalism" in modifier else "Village"
    player.hand = [get_card(name)]
    get_card("Courtier").play_effect(state)
    assert strategy.count == count
    assert player.coins == 3 and player.discard[0].name == "Gold"


def test_courtier_mandatory_reveal_and_bonuses_cannot_be_declined():
    strategy = EnhancedStrategy()
    strategy.choose_courtier_reveal = lambda *_: None
    strategy.choose_courtier_options = lambda *_: None
    state, player = make_state(strategy, ("Courtier", "Minion"))
    player.hand = [get_card("Copper"), get_card("Minion")]
    get_card("Courtier").play_effect(state)
    assert player.coins == 3 and [c.name for c in player.discard] == ["Gold"]


def test_courtier_default_prefers_live_types_over_printed_types():
    state, player = make_state(kingdom=("Courtier", "Militia", "Mill"))
    player.projects = [Capitalism()]
    militia, mill = get_card("Militia"), get_card("Mill")
    player.hand = [mill, militia]
    assert player.ai.choose_courtier_reveal(state, player, player.hand) is militia


@pytest.mark.parametrize("card", ["Courtier", "Stables", "Spice Merchant"])
def test_choice_action_bonuses_respect_snowy_village(card):
    strategy = EnhancedStrategy()
    strategy.choose_courtier_options = lambda *_: ["action"]
    strategy.choose_spice_merchant_mode = lambda *_: "cards"
    state, player = make_state(strategy, (card,))
    player.ignore_action_bonuses = True
    player.hand = [get_card("Copper")]
    player.deck = [get_card("Silver") for _ in range(4)]
    get_card(card).play_effect(state)
    assert player.actions == 0
    assert len(player.hand) == {"Courtier": 1, "Stables": 3, "Spice Merchant": 2}[card]


@pytest.mark.parametrize("answer", [None, "invalid", "Silver"])
def test_rogue_trash_gain_is_mandatory_overridable_and_suppresses_attack(answer):
    strategy = EnhancedStrategy()
    seen = []
    def choose(state, player, choices):
        seen.extend(choices)
        return next((c for c in choices if c.name == answer), get_card("Copper") if answer == "invalid" else None)
    strategy.should_gain_from_trash_with_rogue = choose
    state, player = make_state(strategy, ("Rogue",))
    silver, gold = get_card("Silver"), get_card("Gold")
    state.trash = [silver, gold]
    victim = state.players[1]
    victim.deck = [get_card("Silver"), get_card("Gold")]
    before = list(victim.deck)
    supply = dict(state.supply)
    get_card("Rogue").play_effect(state)
    gained = silver if answer == "Silver" else gold
    assert seen == [silver, gold]
    assert player.discard == [gained] and gained not in state.trash
    assert victim.deck == before and not victim.discard
    assert state.supply == supply


@pytest.mark.parametrize("source", ["Rogue", "Sir Bailey"])
def test_deck_trash_attacks_exclude_potion_and_debt_costs(source):
    state, player = make_state(kingdom=("Rogue", "Knights"))
    potion = Card("Potion priced", CardCost(coins=3, potions=1), CardStats(), [CardType.ACTION])
    debt = Card("Debt priced", CardCost(coins=3, debt=1), CardStats(), [CardType.ACTION])
    victim = state.players[1]
    victim.deck = [potion, debt]
    get_card(source).play_effect(state)
    assert not state.trash
    assert victim.discard == [debt, potion]


def test_rogue_does_not_gain_the_card_its_attack_just_trashed():
    state, player = make_state(kingdom=("Rogue",))
    silver = get_card("Silver")
    state.players[1].deck = [silver]
    get_card("Rogue").play_effect(state)
    assert state.trash == [silver] and player.discard == []


def test_knight_self_trash_resolves_before_the_next_victim_in_turn_order():
    state, _ = make_state(kingdom=("Knights",), players=3)
    state.current_player_index = 1
    attacker = state.current_player
    source = get_card("Sir Vander")
    attacker.in_play = [source]
    state.players[2].deck = [get_card("Dame Anna")]
    state.players[0].deck = [get_card("Sir Vander")]
    state.supply["Gold"] = 1
    source.play_effect(state)
    assert source in state.trash
    assert [c.name for c in attacker.discard] == ["Gold"]
    assert not state.players[0].discard  # Attack still resolves after source leaves.
    assert len(state.trash) == 3


@pytest.mark.parametrize("source,hook", [
    ("Stables", "choose_treasure_to_discard_for_stables"),
    ("Spice Merchant", "choose_treasure_to_trash_for_spice_merchant"),
    ("Counterfeit", "should_replay_treasure_with_counterfeit"),
])
@pytest.mark.parametrize("kind", ["Charlatan", "Capitalism", "Inheritance"])
def test_owned_treasure_menus_include_live_types(source, hook, kind):
    strategy = EnhancedStrategy()
    seen = []
    def choose(state, player, choices):
        seen.extend(choices)
        return choices[0]
    setattr(strategy, hook, choose)
    state, player = make_state(strategy, (source,))
    if kind == "Charlatan":
        state.supply["Charlatan"] = 10
        card = get_card("Curse")
    else:
        player.projects = [Capitalism()]
        if kind == "Inheritance":
            player.inherited_action_name = "Militia"
            card = get_card("Estate")
        else:
            card = get_card("Militia")
    player.hand = [card]
    player.deck = [get_card("Gold") for _ in range(3)]
    get_card(source).play_effect(state)
    if kind == "Inheritance":
        assert seen == [] and card in player.hand
        return  # Inheritance's Command text does not make Estate a Treasure.
    assert seen == [card] and card not in player.hand
    if source == "Counterfeit" and kind == "Capitalism":
        assert player.coins == 4  # Both actual Militia instruction plays resolve.
        assert player.actions_played == 2
        assert state.trash == [card]
        assert card.name == "Militia"


def test_counterfeit_does_not_trash_a_returned_spoils_or_accept_a_non_treasure():
    state, player = make_state(kingdom=("Counterfeit", "Bandit Camp"))
    spoils = get_card("Spoils")
    player.hand = [spoils]
    state.supply["Spoils"] = 4
    get_card("Counterfeit").play_effect(state)
    assert state.supply["Spoils"] == 5 and not state.trash
    assert player.coins == 6
    estate = get_card("Estate")
    player.hand = [estate]
    player.ai.strategy.should_replay_treasure_with_counterfeit = lambda *_: estate
    get_card("Counterfeit").play_effect(state)
    assert player.hand == [estate] and not state.trash


def test_artificer_can_discard_without_a_gain_and_choose_useful_cards():
    strategy = EnhancedStrategy()
    strategy.choose_artificer_discards = lambda s, p, choices: [choices[0], choices[0], get_card("Gold")]
    state, player = make_state(strategy, ("Artificer",))
    silver, estate = get_card("Silver"), get_card("Estate")
    player.hand = [silver, estate]
    get_card("Artificer").play_effect(state)
    assert player.discard == [silver] and player.hand == [estate]
    assert player.deck == []


def test_artificer_zero_discards_can_gain_a_free_card_through_the_fresh_hook():
    strategy = EnhancedStrategy()
    strategy.choose_artificer_discards = lambda *_: []
    strategy.choose_artificer_gain_after_discard = lambda s, p, choices, plan: next(c for c in choices if c.name == "Copper")
    state, player = make_state(strategy, ("Artificer",))
    get_card("Artificer").play_effect(state)
    assert [c.name for c in player.deck] == ["Copper"]


def test_artificer_rebuilds_the_gain_menu_after_discard_reactions():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver")]
    state, player = make_state(strategy, ("Artificer", "Village"))
    player.hand = [get_card("Copper") for _ in range(3)]
    # Isolate a cost change during nested discard-reaction resolution.
    original = state.discard_card
    def discard(owner, card, **kwargs):
        original(owner, card, **kwargs)
        owner.cost_reduction = 1
    state.discard_card = discard
    menus = []
    def gain(s, p, choices, planned):
        menus.append([c.name for c in choices])
        return planned  # Silver now costs $2 and is no longer legal for 3 discards.
    strategy.choose_artificer_gain_after_discard = gain
    get_card("Artificer").play_effect(state)
    assert len(player.discard) == 3 and not player.deck
    assert menus and all("Silver" not in menu for menu in menus)


def test_artificer_cannot_gain_a_pile_member_consumed_by_friendly_discard():
    strategy = EnhancedStrategy()
    strategy.choose_artificer_gain = lambda s, p, choices: next(c for c in choices if c.name == "Village")
    state, player = make_state(strategy, ("Artificer", "Village"))
    village = get_card("Village")
    player.hand = [get_card("Copper"), get_card("Copper"), village]
    state.supply["Village"] = 1
    state.pile_traits["Village"] = "Friendly"
    menus = []
    def after(s, p, choices, planned):
        menus.append([c.name for c in choices])
        return planned
    strategy.choose_artificer_gain_after_discard = after
    get_card("Artificer").play_effect(state)
    assert state.supply["Village"] == 0
    assert player.count("Village") == 2  # Original discard and Friendly's gain.
    assert not player.deck and all("Village" not in menu for menu in menus)
