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
    state, player = make_state(kingdom=("Courtier", "Militia", "Great Hall"))
    player.projects = [Capitalism()]
    militia, mill = get_card("Militia"), get_card("Great Hall")
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


@pytest.mark.parametrize("name", ["Merchant Ship", "Search", "Frigate"])
def test_counterfeit_excludes_capitalism_duration_treasures(name):
    state, player = make_state(kingdom=("Counterfeit", name))
    player.projects = [Capitalism()]
    card = get_card(name)
    player.hand = [card]
    assert state.is_treasure(card) and card.is_duration
    player.ai.strategy.should_replay_treasure_with_counterfeit = lambda *_: pytest.fail("No legal target")
    get_card("Counterfeit").play_effect(state)
    assert player.hand == [card]
    assert not player.duration and not player.in_play and not state.trash


@pytest.mark.parametrize("copies", [1, 2])
def test_counterfeit_checks_warlord_before_moving_then_allows_legal_replays(copies):
    state, player = make_state(kingdom=("Counterfeit", "Militia", "Warlord"))
    player.projects = [Capitalism()]
    player.warlord_restriction_count = 1
    militia = get_card("Militia")
    player.hand = [militia]
    player.in_play = [get_card("Militia") for _ in range(copies)]
    get_card("Counterfeit").play_effect(state)
    if copies == 2:
        assert player.hand == [militia] and militia not in state.trash
        assert player.coins == 0 and player.actions_played == 0
    else:
        assert not player.hand and militia in state.trash
        assert player.coins == 4 and player.actions_played == 2


@pytest.mark.parametrize("first", ["trader", "card_on_gain"])
@pytest.mark.parametrize("off_turn", [False, True])
def test_trader_preserves_original_gain_and_on_gain_after_exchange(first, off_turn):
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Duchy")]
    strategy.choose_gain_effect = lambda s, p, card, choices: next(
        (c for c in choices if c.kind == first), choices[0]
    )
    state, player = make_state(strategy, ("Trader", "Border Village"))
    state.current_player_index = int(off_turn)
    player.hand = [get_card("Trader")]
    player.ai.strategy.should_reveal_trader = lambda *_args, **_kwargs: True
    observed = []
    result = state.gain_from_supply(player, "Border Village", gain_observer=observed.append)
    assert result.name == "Silver" and result in player.discard
    assert [c.name for c in observed] == ["Border Village"]
    assert player.gained_cards_this_turn == ["Border Village", "Duchy"]
    assert [c.name for c in player.discard] == ["Silver", "Silver"]
    assert state.supply["Border Village"] == 10 and state.supply["Duchy"] == 8
    assert state.current_player_index == int(off_turn)


@pytest.mark.parametrize("first", ["trader", "watchtower"])
def test_trader_obeys_owner_order_and_cannot_follow_a_moved_gain(first):
    strategy = EnhancedStrategy()
    strategy.choose_gain_effect = lambda s, p, card, choices: next(
        (c for c in choices if c.kind == first), choices[0]
    )
    strategy.choose_watchtower_reaction = lambda *_: "trash"
    state, player = make_state(strategy, ("Trader", "Watchtower"))
    player.hand = [get_card("Trader"), get_card("Watchtower")]
    player.ai.strategy.should_reveal_trader = lambda *_args, **_kwargs: True
    silvers, golds = state.supply["Silver"], state.supply["Gold"]
    state.gain_from_supply(player, "Gold")
    assert player.gained_cards_this_turn == ["Gold"]
    if first == "trader":
        assert [c.name for c in player.discard] == ["Silver"]
        assert state.supply["Silver"] == silvers - 1 and state.supply["Gold"] == golds
        assert not state.trash
    else:
        assert [c.name for c in state.trash] == ["Gold"]
        assert state.supply["Silver"] == silvers and state.supply["Gold"] == golds - 1
        assert not player.discard


@pytest.mark.parametrize("name,capitalism,bonus_horse,victory", [
    ("Village", False, True, False), ("Mill", False, True, True),
    ("Estate", False, False, True), ("Militia", True, True, False),
])
def test_groom_bonuses_use_original_live_types_after_trader(name, capitalism, bonus_horse, victory):
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule(name)]
    strategy.should_reveal_trader = lambda s, p, card, **kw: card.name == name
    state, player = make_state(strategy, ("Groom", "Trader", "Village", "Mill", "Militia"))
    if capitalism:
        player.projects = [Capitalism()]
    player.hand = [get_card("Trader")]
    player.deck = [get_card("Gold")]
    get_card("Groom").play_effect(state)
    assert player.gained_cards_this_turn[0] == name
    assert sum(c.name == "Horse" for c in player.discard) == bonus_horse
    assert sum(c.name == "Silver" for c in player.discard) == (2 if capitalism else 1)
    assert player.actions == int(victory)
    assert any(c.name == "Gold" for c in player.hand) == victory
    assert not state.players[1].discard


def test_groom_victory_draw_respects_snowy_village_action_suppression():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Estate")]
    state, player = make_state(strategy, ("Groom",))
    player.ignore_action_bonuses = True
    player.deck = [get_card("Gold")]
    get_card("Groom").play_effect(state)
    assert player.actions == 0 and [c.name for c in player.hand] == ["Gold"]


@pytest.mark.parametrize("target,trash", [("Estate", "Copper"), ("Mill", "Estate")])
def test_replace_attacks_for_original_victory_gain_after_trader(target, trash):
    strategy = EnhancedStrategy()
    strategy.trash_priority = [PriorityRule(trash)]
    strategy.should_reveal_trader = lambda s, p, card, **kw: card.name == target
    state, player = make_state(strategy, ("Replace", "Mill", "Trader"))
    player.hand = [get_card(trash), get_card("Trader")]
    player.ai.choose_card_to_gain_for_replace = lambda *_: get_card(target)
    get_card("Replace").play_effect(state)
    assert player.gained_cards_this_turn == [target]
    assert [c.name for c in player.discard] == ["Silver"]
    assert not player.deck
    assert [c.name for c in state.players[1].discard] == ["Curse"]


def test_wild_hunt_scores_original_estate_gain_after_trader_exchange():
    strategy = EnhancedStrategy()
    strategy.should_reveal_trader = lambda s, p, card, **kw: card.name == "Estate"
    state, player = make_state(strategy, ("Wild Hunt", "Trader"))
    player.hand = [get_card("Trader")]
    player.ai.choose_wild_hunt_option = lambda *_: "estate"
    state.wild_hunt_pile_tokens = 3
    get_card("Wild Hunt").play_effect(state)
    assert player.gained_cards_this_turn == ["Estate"]
    assert player.vp_tokens == 3 and state.wild_hunt_pile_tokens == 0
    assert [c.name for c in player.discard] == ["Silver"]


def test_hoard_purchase_bonus_uses_original_victory_card_after_trader():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Estate")]
    strategy.should_reveal_trader = lambda s, p, card, **kw: card.name == "Estate"
    state, player = make_state(strategy, ("Hoard", "Trader"))
    player.hand = [get_card("Trader")]
    player.in_play = [get_card("Hoard")]
    player.coins, player.buys = 2, 1
    state.phase = "buy"
    state.handle_buy_phase()
    assert player.gained_cards_this_turn == ["Estate", "Gold"]
    assert sorted(c.name for c in player.discard) == ["Gold", "Silver"]


def test_rebuild_does_not_restore_twice_after_trader_and_nested_duplicate():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Dame Josephine")]
    strategy.choose_gain_effect = lambda s, p, card, choices: next(
        (c for c in choices if c.kind == "trader"), choices[0]
    )
    trades = []
    def reveal(s, p, card, **kw):
        if card.name == "Dame Josephine" and not trades:
            trades.append(card)
            return True
        return False
    strategy.should_reveal_trader = reveal
    state, player = make_state(strategy, ("Rebuild", "Trader", "Duplicate", "Knights"))
    state.pile_order["Knights"].remove("Dame Josephine")
    state.pile_order["Knights"].append("Dame Josephine")
    player.hand = [get_card("Trader")]
    player.deck = [get_card("Estate")]
    player.tavern_mat = [get_card("Duplicate")]
    player.ai.should_call_from_tavern = lambda *_: True
    count = state.supply["Knights"]
    get_card("Rebuild").play_effect(state)
    assert state.supply["Knights"] == count - 1
    assert len(state.pile_order["Knights"]) == count - 1
    assert sorted(c.name for c in player.discard) == ["Dame Josephine", "Silver"]


@pytest.mark.parametrize("reaction", [None, "trader", "topdeck", "trash"])
@pytest.mark.parametrize("own_turn", [False, True])
def test_blockade_watches_only_a_real_set_aside_on_the_gainers_own_turn(reaction, own_turn):
    strategy = EnhancedStrategy()
    strategy.should_reveal_trader = lambda *_args, **_kwargs: reaction == "trader"
    strategy.choose_watchtower_reaction = lambda *_: reaction
    state, player = make_state(strategy, ("Blockade", "Trader", "Watchtower", "Village"))
    player.ai.choose_card_to_gain_with_blockade = lambda *_args, **_kwargs: get_card("Village")
    player.hand = [get_card("Trader")] if reaction == "trader" else [get_card("Watchtower")] if reaction else []
    blockade = get_card("Blockade")
    player.in_play = [blockade]
    blockade.play_effect(state)
    assert bool(blockade.set_aside) == (reaction is None)
    assert (blockade in player.duration) == (reaction is None)
    state.current_player_index = int(own_turn)
    victim = state.players[1]
    state.gain_from_supply(victim, "Village")
    curses = int(reaction is None and own_turn)
    assert victim.count("Curse") == curses
    state.current_player_index = 0
    blockade.on_duration(state)
    state.current_player_index = 1
    state.gain_from_supply(victim, "Village")
    assert victim.count("Curse") == curses  # No watcher after returning the card.


def test_failed_blockade_replay_preserves_its_existing_payload_and_immunity_snapshot():
    state, player = make_state(kingdom=("Blockade", "Trader", "Village", "Lighthouse"))
    player.ai.choose_card_to_gain_with_blockade = lambda *_args, **_kwargs: get_card("Village")
    blockade = get_card("Blockade")
    player.in_play = [blockade]
    blockade.play_effect(state)
    stored = blockade.set_aside[0]
    player.hand = [get_card("Trader")]
    player.ai.strategy.should_reveal_trader = lambda *_args, **_kwargs: True
    state.players[1].duration = [get_card("Lighthouse")]
    blockade.play_effect(state)
    assert blockade.set_aside == [stored] and player.duration == [blockade]
    state.current_player_index = 1
    state.gain_from_supply(state.players[1], "Village")
    assert state.players[1].count("Curse") == 1  # Still the earlier unblocked attack.


@pytest.mark.parametrize("name,pile", [("Gold", "Gold"), ("Sir Bailey", "Knights"), ("Ghost", "Ghost")])
def test_rogue_trader_returns_trash_gain_to_its_physical_pile(name, pile):
    state, player = make_state(kingdom=("Rogue", "Trader", "Knights", "Exorcist"))
    if pile == "Knights":
        # Expose the desired member, then take exactly that physical copy.
        state.pile_order[pile].remove(name)
        state.pile_order[pile].append(name)
    card = state.take_top_supply_card(pile)
    assert card.name == name
    state.trash = [card]
    player.hand = [get_card("Trader")]
    player.ai.strategy.should_reveal_trader = lambda *_args, **_kwargs: True
    count = state.supply[pile]
    silvers = state.supply["Silver"]
    get_card("Rogue").play_effect(state)
    assert card not in state.trash and card not in player.all_cards()
    assert card.returned_to_supply
    assert state.supply[pile] == count + 1
    assert state.top_supply_card(pile) == name
    assert state.supply["Silver"] == silvers - 1
    assert [c.name for c in player.discard] == ["Silver"]


def test_rogue_trader_cannot_exchange_a_card_without_an_origin_pile():
    state, player = make_state(kingdom=("Rogue", "Trader", "Necromancer"))
    spy = next(c for c in state.trash if c.name == "Zombie Spy")
    state.trash = [spy]
    player.hand = [get_card("Trader")]
    player.ai.strategy.should_reveal_trader = lambda *_args, **_kwargs: True
    silvers = state.supply["Silver"]
    get_card("Rogue").play_effect(state)
    assert player.discard == [spy]
    assert state.supply["Silver"] == silvers


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


@pytest.mark.parametrize("name", ["Nomad Camp", "Ghost Town", "Guardian", "Night Watchman", "Den of Sin"])
@pytest.mark.parametrize("reaction", [None, "trader", "topdeck", "trash"])
def test_blockade_initial_storage_overrides_printed_placement_before_gain_reactions(name, reaction):
    state, player = make_state(kingdom=("Blockade", name, "Trader", "Watchtower"))
    player.cost_reduction = 1  # Includes a legal reduced-cost Den of Sin.
    player.ai.choose_card_to_gain_with_blockade = lambda *_args, **_kwargs: get_card(name)
    player.ai.should_play_night_watchman_now = lambda *_: True
    player.hand = [get_card("Trader")] if reaction == "trader" else [get_card("Watchtower")]
    player.ai.strategy.should_reveal_trader = lambda *_args, **_kwargs: reaction == "trader"
    observed = []
    def watch(s, p, card):
        if card.name == name:
            observed.append(card)
            assert card in p.pending_gain_set_aside and p.count(name) == 1
            assert card not in p.hand + p.deck + p.discard + p.in_play
        return reaction
    player.ai.strategy.choose_watchtower_reaction = watch
    blockade = get_card("Blockade")
    player.in_play = [blockade]
    count = state.supply[name]
    blockade.play_effect(state)
    assert not player.pending_gain_set_aside
    assert bool(blockade.set_aside) == (reaction is None)
    assert state.supply[name] == count - int(reaction != "trader")
    state.current_player_index = 1
    state.gain_from_supply(state.players[1], name)
    assert state.players[1].count("Curse") == int(reaction is None)
    state.current_player_index = 0
    if reaction is None:
        stored = blockade.set_aside[0]
        assert stored is observed[0] and player.count(name) == 1
        blockade.on_duration(state)
        assert stored in player.hand and player.count(name) == 1
        state.current_player_index = 1
        state.gain_from_supply(state.players[1], name)
        assert state.players[1].count("Curse") == 1
    elif reaction == "trader":
        assert player.count(name) == 0 and any(c.name == "Silver" for c in player.discard)
    elif reaction == "trash":
        assert observed[0] in state.trash and player.count(name) == 0
    else:
        assert player.deck[-1] is observed[0] and player.count(name) == 1
    assert not any(c.name == name for c in player.in_play)


@pytest.mark.parametrize("name", ["Nomad Camp", "Ghost Town", "Guardian", "Night Watchman", "Den of Sin"])
@pytest.mark.parametrize("destination", ["default", "deck", "hand"])
@pytest.mark.parametrize("trash", [False, True])
def test_printed_gain_placement_is_initial_and_yields_to_an_explicit_source(name, destination, trash):
    state, player = make_state(kingdom=(name, "Watchtower"))
    player.hand = [get_card("Watchtower")]
    player.ai.should_play_night_watchman_now = lambda *_: True
    expected = "deck" if name == "Nomad Camp" else "hand"
    if destination != "default":
        expected = destination
    observed = []
    def watch(s, p, card):
        observed.append(card)
        assert card in getattr(p, expected)
        return "trash" if trash else None
    player.ai.strategy.choose_watchtower_reaction = watch
    card = get_card(name)
    state.gain_card(player, card, from_supply=False,
                    to_deck=destination == "deck", to_hand=destination == "hand")
    assert observed == [card]
    assert (card in state.trash) == trash
    assert player.count(name) == int(not trash)
    assert card not in player.in_play


def test_villa_moves_from_blockade_initial_storage_without_arming_a_watcher():
    state, player = make_state(kingdom=("Blockade", "Villa"))
    player.ai.choose_card_to_gain_with_blockade = lambda *_args, **_kwargs: get_card("Villa")
    blockade = get_card("Blockade")
    player.in_play = [blockade]
    blockade.play_effect(state)
    assert [c.name for c in player.hand] == ["Villa"] and player.actions == 1
    assert not player.pending_gain_set_aside and not blockade.set_aside
    assert blockade not in player.duration and not blockade.pending_plays
    state.current_player_index = 1
    state.gain_from_supply(state.players[1], "Villa")
    assert state.players[1].count("Curse") == 0


@pytest.mark.parametrize("name", ["Nomad Camp", "Ghost Town", "Guardian", "Night Watchman", "Den of Sin"])
@pytest.mark.parametrize("reaction", [None, "trader", "trash"])
def test_forge_uses_printed_initial_destinations_and_the_shared_gain_event(name, reaction):
    state, player = make_state(kingdom=("Forge", name, "Trader", "Watchtower"))
    doomed = get_card(name)
    player.hand = [doomed, get_card("Trader" if reaction == "trader" else "Watchtower")]
    player.ai.choose_card_to_trash = lambda _s, choices: doomed if doomed in choices else None
    player.ai.choose_buy = lambda _s, choices: next(c for c in choices if c is not None and c.name == name)
    player.ai.strategy.should_reveal_trader = lambda *_a, **_k: reaction == "trader"
    observed = []
    def watch(s, p, card):
        observed.append(card)
        assert card in (p.deck if name == "Nomad Camp" else p.hand)
        return "trash" if reaction == "trash" else None
    player.ai.strategy.choose_watchtower_reaction = watch
    count = state.supply[name]
    get_card("Forge").play_effect(state)
    assert doomed in state.trash
    assert player.gained_cards_this_turn == [name]
    assert state.supply[name] == count - int(reaction != "trader")
    assert player.count(name) == int(reaction is None)
    if reaction == "trash":
        assert observed[0] in state.trash and observed[0] is not doomed
    elif reaction == "trader":
        assert any(c.name == "Silver" for c in player.discard)
    else:
        assert observed[0] in (player.deck if name == "Nomad Camp" else player.hand)


@pytest.mark.parametrize("name", ["Trail", "Berserker", "Buried Treasure"])
@pytest.mark.parametrize("move_first", [False, True])
def test_on_gain_self_plays_recognize_blockade_storage_and_stop_after_prior_movement(name, move_first):
    state, player = make_state(kingdom=("Blockade", name, "Watchtower"))
    player.deck = [get_card("Copper")]
    state.players[1].hand = [get_card("Copper") for _ in range(5)]
    player.cost_reduction = 1
    player.ai.choose_card_to_gain_with_blockade = lambda *_a, **_k: get_card(name)
    player.ai.choose_action = lambda _s, choices: next((c for c in choices if c is not None and c.name == "Trail"), None)
    # Berserker's nested gain has a harmless, fixed target.
    player.ai.choose_buy = lambda _s, choices: next((c for c in choices if c is not None and c.name == "Silver"), None)
    if move_first:
        player.hand = [get_card("Watchtower")]
        player.ai.strategy.choose_watchtower_reaction = lambda _s, _p, card: "topdeck" if card.name == name else None
        player.ai.strategy.choose_gain_effect = lambda _s, _p, card, choices: next(
            (c for c in choices if c.kind == "watchtower"), choices[0]
        )
    blockade = get_card("Blockade")
    player.in_play = [blockade]
    blockade.play_effect(state)
    assert not blockade.set_aside and blockade not in player.duration
    assert not player.pending_gain_set_aside and player.count(name) == 1
    if not move_first:
        assert any(c.name == name for c in player.in_play)
        if name == "Trail":
            assert player.actions == 1 and [c.name for c in player.hand] == ["Copper"]
        elif name == "Berserker":
            assert player.gained_cards_this_turn == ["Berserker", "Silver"]
            assert len(state.players[1].hand) == 3
        else:
            assert any(c.name == name for c in player.duration)
    else:
        assert player.deck[-1].name == name
        assert not any(c.name == name for c in player.in_play)
    state.current_player_index = 1
    state.gain_from_supply(state.players[1], name)
    assert state.players[1].count("Curse") == 0


def test_declined_trail_gain_reaction_preserves_blockade_storage_and_next_turn_return():
    state, player = make_state(kingdom=("Blockade", "Trail"))
    player.ai.choose_card_to_gain_with_blockade = lambda *_a, **_k: get_card("Trail")
    player.ai.choose_action = lambda *_: None
    blockade = get_card("Blockade")
    player.in_play = [blockade]
    blockade.play_effect(state)
    stored = blockade.set_aside[0]
    assert stored.name == "Trail" and player.count("Trail") == 1
    assert not player.pending_gain_set_aside and player.duration == [blockade]
    assert not any(c.name == "Trail" for c in player.in_play)
    state.current_player_index = 1
    state.gain_from_supply(state.players[1], "Trail")
    assert state.players[1].count("Curse") == 1
    state.current_player_index = 0
    blockade.on_duration(state)
    assert player.hand == [stored] and not blockade.set_aside
    assert player.count("Trail") == 1 and player.actions == 0
