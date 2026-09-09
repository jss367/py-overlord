"""Rules regressions found by the Kolkata board card audit.

Kingdom: Artist, Artificer, Armory, Bandit Camp, Bard, Knights, Research,
Scheme, Spice Merchant, Stables.
"""

import random

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


class _PickAI(ChooseFirstActionAI):
    """Test AI whose gain/trash choices can be scripted by name."""

    def __init__(self, wants=()):
        super().__init__()
        self.wants = list(wants)

    def _pick(self, choices):
        for name in self.wants:
            for card in choices:
                if card is not None and card.name == name:
                    return card
        return None

    def choose_buy(self, state, choices):
        return self._pick(choices)

    def choose_card_to_trash(self, state, choices):
        return self._pick(choices)

    def choose_treasure(self, state, choices):
        return next((c for c in choices if c is not None), None)


def _setup(kingdom, num_players=2, wants=()):
    ais = [_PickAI(wants) for _ in range(num_players)]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card(name) for name in kingdom])
    for p in state.players:
        p.hand = []
        p.deck = []
        p.discard = []
        p.in_play = []
        p.duration = []
        p.actions = 1
        p.buys = 1
        p.coins = 0
    return state


# ---------------------------------------------------------------- Knights


def test_knight_attack_gives_no_coins():
    state = _setup(["Knights"])
    attacker, victim = state.players
    destry = get_card("Sir Destry")
    attacker.in_play.append(destry)
    attacker.deck = [get_card("Copper"), get_card("Copper")]
    victim.deck = [get_card("Copper"), get_card("Silver")]

    destry.play_effect(state)

    assert attacker.coins == 0
    assert any(c.name == "Silver" for c in state.trash)


def test_dame_sylvia_is_the_only_knight_with_coins():
    state = _setup(["Knights"])
    attacker, victim = state.players
    sylvia = get_card("Dame Sylvia")
    attacker.in_play.append(sylvia)
    victim.deck = [get_card("Copper"), get_card("Copper")]

    state.play_card = None  # ensure we go through the card's own effect
    attacker.coins += sylvia.stats.coins
    sylvia.play_effect(state)

    assert attacker.coins == 2


def test_sir_martin_costs_four_and_gives_two_buys():
    martin = get_card("Sir Martin")
    assert martin.cost.coins == 4
    assert martin.stats.buys == 2


def test_knight_attack_victim_chooses_and_prefers_trashing_a_knight():
    state = _setup(["Knights"])
    attacker, victim = state.players
    bailey = get_card("Sir Bailey")
    attacker.in_play.append(bailey)
    attacker.deck = [get_card("Copper")]
    # Both revealed cards qualify ($3-$6). The victim gives up its Knight
    # so that the attacking Knight is trashed as well.
    natalie = get_card("Dame Natalie")
    gold = get_card("Gold")
    victim.deck = [natalie, gold]

    bailey.play_effect(state)

    assert natalie in state.trash
    assert bailey in state.trash
    assert gold in victim.discard


def test_knight_attack_victim_default_trashes_cheapest_card():
    state = _setup(["Knights"])
    attacker, victim = state.players
    destry = get_card("Sir Destry")
    attacker.in_play.append(destry)
    attacker.deck = [get_card("Copper"), get_card("Copper")]
    silver = get_card("Silver")
    gold = get_card("Gold")
    victim.deck = [gold, silver]

    destry.play_effect(state)

    assert silver in state.trash
    assert gold in victim.discard


def test_knight_attack_victim_hook_is_forwarded_to_the_strategy():
    from dominion.ai.genetic_ai import GeneticAI
    from dominion.strategy.strategies.big_money import create_big_money

    strategy = create_big_money()
    strategy.choose_card_to_trash_for_knight_attack = (
        lambda state, player, choices: max(choices, key=lambda c: c.cost.coins)
    )
    ai = GeneticAI(strategy)
    state = GameState(players=[])
    state.initialize_game([ai, _PickAI()], [get_card("Knights")])
    gold = get_card("Gold")
    silver = get_card("Silver")
    chosen = ai.choose_card_to_trash_for_knight_attack(
        state, state.players[0], [silver, gold]
    )
    assert chosen is gold


# -------------------------------------------------------------- Artificer


def test_artificer_gains_onto_the_deck_not_into_hand():
    state = _setup(["Artificer", "Stables"], wants=["Stables"])
    player = state.current_player
    player.hand = [get_card("Copper") for _ in range(5)]
    player.deck = [get_card("Silver")]

    artificer = get_card("Artificer")
    player.in_play.append(artificer)
    artificer.play_effect(state)

    assert player.deck[-1].name == "Stables"
    assert not any(c.name == "Stables" for c in player.hand)
    assert len(player.hand) == 0
    assert sum(1 for c in player.discard if c.name == "Copper") == 5


def test_artificer_default_only_spends_junk_and_skips_free_gains():
    state = _setup(["Artificer", "Bandit Camp"], wants=["Bandit Camp", "Copper"])
    player = state.current_player
    # Two junk cards and three good ones: a $5 would need good cards, and a
    # $0 Copper is never taken by default. Nothing should be gained.
    player.hand = [
        get_card("Copper"), get_card("Estate"),
        get_card("Gold"), get_card("Gold"), get_card("Bandit Camp"),
    ]
    player.deck = [get_card("Silver")]
    before = len(player.hand)

    artificer = get_card("Artificer")
    player.in_play.append(artificer)
    artificer.play_effect(state)

    assert len(player.hand) == before
    assert player.deck == [player.deck[0]] and player.deck[0].name == "Silver"


def test_artificer_can_gain_the_top_knight():
    random.seed(3)
    state = _setup(["Artificer", "Knights"])
    player = state.current_player
    top = state.pile_order["Knights"][-1]
    player.ai.wants = [top]
    cost = get_card(top).cost.coins
    player.hand = [get_card("Copper") for _ in range(cost)]
    player.deck = []

    artificer = get_card("Artificer")
    player.in_play.append(artificer)
    artificer.play_effect(state)

    assert player.deck and player.deck[-1].name == top
    assert state.pile_order["Knights"][-1] != top or state.supply["Knights"] == 9
    assert state.supply["Knights"] == 9


# ----------------------------------------------------------------- Armory


def test_armory_asks_the_ai_and_topdecks_the_gain():
    state = _setup(["Armory", "Research"], wants=["Research"])
    player = state.current_player
    player.deck = [get_card("Copper")]

    armory = get_card("Armory")
    player.in_play.append(armory)
    armory.play_effect(state)

    assert player.deck[-1].name == "Research"
    assert state.supply["Research"] == 9


def test_armory_can_gain_sir_martin_from_the_top_of_the_knights_pile():
    state = _setup(["Armory", "Knights"], wants=["Sir Martin"])
    state.pile_order["Knights"].remove("Sir Martin")
    state.pile_order["Knights"].append("Sir Martin")
    player = state.current_player
    player.deck = []

    armory = get_card("Armory")
    player.in_play.append(armory)
    armory.play_effect(state)

    assert player.deck and player.deck[-1].name == "Sir Martin"
    assert state.supply["Knights"] == 9
    assert "Sir Martin" not in state.pile_order["Knights"]


# ------------------------------------------------------------------ Scheme


def test_scheme_does_not_topdeck_a_duration_that_stays_in_play():
    state = _setup(["Scheme", "Research"])
    player = state.current_player
    research = get_card("Research")
    scheme = get_card("Scheme")
    player.in_play = [scheme, research]
    player.duration = [research]
    research.duration_persistent = True
    player.hand = []
    player.deck = [get_card("Copper") for _ in range(5)]
    player.discard = []

    state.phase = "cleanup"
    state.handle_cleanup_phase()

    assert research in player.in_play
    assert research not in player.deck
    # Scheme itself was the only discardable Action, so it went on the deck
    # and was drawn back into the new hand.
    assert scheme in player.hand


def test_scheme_topdeck_choice_is_forwarded_to_the_strategy():
    from dominion.ai.genetic_ai import GeneticAI
    from dominion.strategy.strategies.big_money import create_big_money

    strategy = create_big_money()
    strategy.choose_card_to_topdeck_for_scheme = (
        lambda state, player, choices: next(c for c in choices if c.name == "Scheme")
    )
    ai = GeneticAI(strategy)
    state = GameState(players=[])
    state.initialize_game([ai, _PickAI()], [get_card("Scheme"), get_card("Stables")])
    player = state.players[0]
    scheme = get_card("Scheme")
    stables = get_card("Stables")
    player.in_play = [scheme, stables]
    player.hand = []
    player.duration = []
    player.deck = [get_card("Copper") for _ in range(5)]
    player.discard = []
    state.current_player_index = 0

    state.phase = "cleanup"
    state.handle_cleanup_phase()

    assert scheme in player.hand
    assert stables in player.discard


# ---------------------------------------------------------- Spice Merchant


def test_spice_merchant_is_optional_and_does_not_trash_silver_by_default():
    state = _setup(["Spice Merchant"])
    player = state.current_player
    silver = get_card("Silver")
    player.hand = [silver, get_card("Estate")]
    player.deck = [get_card("Copper") for _ in range(3)]

    merchant = get_card("Spice Merchant")
    player.in_play.append(merchant)
    merchant.play_effect(state)

    assert silver in player.hand
    assert not state.trash
    assert len(player.hand) == 2


def test_spice_merchant_trashes_copper_and_uses_the_chosen_mode():
    state = _setup(["Spice Merchant"])
    player = state.current_player
    player.ai.choose_spice_merchant_mode = lambda state, p: "coins"
    copper = get_card("Copper")
    player.hand = [copper, get_card("Silver")]
    player.deck = [get_card("Copper") for _ in range(3)]

    merchant = get_card("Spice Merchant")
    player.in_play.append(merchant)
    merchant.play_effect(state)

    assert copper in state.trash
    assert player.coins == 2
    assert player.buys == 2
    assert len(player.hand) == 1


# ----------------------------------------------------------------- Stables


def test_stables_discards_spoils_before_silver_by_default():
    state = _setup(["Stables", "Bandit Camp"])
    player = state.current_player
    spoils = get_card("Spoils")
    silver = get_card("Silver")
    player.hand = [silver, spoils]
    player.deck = [get_card("Copper") for _ in range(4)]

    stables = get_card("Stables")
    player.in_play.append(stables)
    stables.play_effect(state)

    assert spoils in player.discard
    assert silver in player.hand
    assert len(player.hand) == 4
    assert player.actions == 2


def test_stables_can_decline_to_discard():
    state = _setup(["Stables"])
    player = state.current_player
    player.ai.choose_treasure_to_discard_for_stables = lambda s, p, choices: None
    gold = get_card("Gold")
    player.hand = [gold]
    player.deck = [get_card("Copper") for _ in range(4)]

    stables = get_card("Stables")
    player.in_play.append(stables)
    stables.play_effect(state)

    assert player.hand == [gold]
    assert player.actions == 1


# ------------------------------------------------------- Knights in rules


def test_a_knights_rule_matches_the_top_knight_and_counts_all_knights():
    from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

    strategy = EnhancedStrategy()
    strategy.gain_priority = [
        PriorityRule("Knights", PriorityRule.max_in_deck("Knights", 2)),
        PriorityRule("Silver"),
    ]
    state = _setup(["Knights"])
    player = state.current_player
    top = get_card(state.pile_order["Knights"][-1])
    silver = get_card("Silver")

    assert strategy.choose_gain(state, player, [silver, top, None]) is top

    player.discard = [get_card("Sir Bailey"), get_card("Dame Anna")]
    assert player.count_in_deck("Knights") == 2
    assert strategy.choose_gain(state, player, [silver, top, None]) is silver


# ---------------------------------------------------------- Best Found


def test_kolkata_best_found_keeps_coppers_and_plays_spoils():
    from generated_strategies.kolkata_best_found import create_kolkata_best_found

    strategy = create_kolkata_best_found()
    state = _setup(["Bandit Camp", "Stables"])
    player = state.current_player
    copper = get_card("Copper")
    estate = get_card("Estate")
    spoils = get_card("Spoils")

    assert strategy.choose_trash(state, player, [copper, estate]) is estate
    assert strategy.choose_trash(state, player, [copper]) is None
    assert strategy.choose_treasure(state, player, [spoils, None]) is spoils


# ----------------------------------------------- Review regressions (#363)


def test_artificer_only_offers_the_exposed_card_of_a_split_pile():
    from dominion.cards.adventures.artificer import _exposed_supply_card

    state = _setup(["Artificer", "Catapult"], wants=["Rocks"])
    player = state.current_player
    # Rocks costs $4 but sits under the Catapults: it must not be offered
    # while a Catapult is on top, and Catapult stays a $3 candidate.
    assert _exposed_supply_card(state, "Rocks") is None
    assert _exposed_supply_card(state, "Catapult").name == "Catapult"

    player.hand = [get_card("Copper") for _ in range(4)]
    player.deck = []
    artificer = get_card("Artificer")
    player.in_play.append(artificer)
    artificer.play_effect(state)

    # Rocks was the only wanted card, so nothing is gained or discarded.
    assert player.deck == []
    assert len(player.hand) == 4
    assert state.supply["Catapult"] == 5 and state.supply["Rocks"] == 5

    # Once the Catapults are gone, Rocks is exposed and the gain takes it.
    state.supply["Catapult"] = 0
    assert _exposed_supply_card(state, "Catapult") is None
    assert _exposed_supply_card(state, "Rocks").name == "Rocks"
    artificer.play_effect(state)

    assert player.deck and player.deck[-1].name == "Rocks"
    assert state.supply["Rocks"] == 4
    assert len(player.hand) == 0


def test_knight_attack_uses_the_attackers_cost_reduction():
    state = _setup(["Knights", "Highway"])
    attacker, victim = state.players
    destry = get_card("Sir Destry")
    attacker.in_play.append(destry)
    attacker.deck = [get_card("Copper"), get_card("Copper")]
    # Highway in the attacker's play: a $7 card costs $6 and is trashable.
    attacker.cost_reduction = 1
    forge = get_card("Forge")
    copper = get_card("Copper")
    victim.deck = [copper, forge]

    destry.play_effect(state)

    assert forge in state.trash
    assert copper in victim.discard


def test_knight_attack_ignores_the_victims_cost_reduction():
    state = _setup(["Knights", "Highway"])
    attacker, victim = state.players
    destry = get_card("Sir Destry")
    attacker.in_play.append(destry)
    attacker.deck = [get_card("Copper"), get_card("Copper")]
    # A stale reduction on the victim must not make a $7 card eligible.
    victim.cost_reduction = 1
    forge = get_card("Forge")
    copper = get_card("Copper")
    victim.deck = [copper, forge]

    destry.play_effect(state)

    assert not state.trash
    assert forge in victim.discard and copper in victim.discard


def test_rogue_attack_uses_the_attackers_cost_reduction():
    state = _setup(["Rogue", "Highway"])
    attacker, victim = state.players
    rogue = get_card("Rogue")
    attacker.in_play.append(rogue)
    attacker.ai.should_gain_from_trash_with_rogue = lambda s, p, choices: None
    attacker.cost_reduction = 1
    forge = get_card("Forge")
    copper = get_card("Copper")
    victim.deck = [copper, forge]

    rogue.play_effect(state)

    assert forge in state.trash
    assert copper in victim.discard


def test_stables_rejects_a_non_treasure_returned_by_the_hook():
    state = _setup(["Stables"])
    player = state.current_player
    estate = get_card("Estate")
    gold = get_card("Gold")
    player.hand = [gold, estate]
    player.deck = [get_card("Copper") for _ in range(4)]
    player.ai.choose_treasure_to_discard_for_stables = lambda s, p, choices: estate

    stables = get_card("Stables")
    player.in_play.append(stables)
    stables.play_effect(state)

    assert player.hand == [gold, estate]
    assert not player.discard
    assert player.actions == 1


def test_spice_merchant_rejects_a_non_treasure_returned_by_the_hook():
    state = _setup(["Spice Merchant"])
    player = state.current_player
    estate = get_card("Estate")
    copper = get_card("Copper")
    player.hand = [copper, estate]
    player.deck = [get_card("Copper") for _ in range(3)]
    player.ai.choose_treasure_to_trash_for_spice_merchant = (
        lambda s, p, choices: estate
    )

    merchant = get_card("Spice Merchant")
    player.in_play.append(merchant)
    merchant.play_effect(state)

    assert player.hand == [copper, estate]
    assert not state.trash
    assert player.coins == 0 and player.buys == 1 and player.actions == 1


def test_artificer_discards_budgeted_junk_before_cheap_useful_cards():
    # Duchy + Copper budget a $2 gain. The generic discard ordering ranks by
    # printed cost and would throw the $3 Scheme before the $5 Duchy.
    state = _setup(["Artificer", "Scheme", "Cellar"], wants=["Cellar"])
    player = state.current_player
    duchy, copper, scheme = get_card("Duchy"), get_card("Copper"), get_card("Scheme")
    golds = [get_card("Gold"), get_card("Gold")]
    player.hand = [duchy, copper, scheme, *golds]
    player.deck = []

    artificer = get_card("Artificer")
    player.in_play.append(artificer)
    artificer.play_effect(state)

    assert player.deck and player.deck[-1].name == "Cellar"
    assert sorted(c.name for c in player.discard) == ["Copper", "Duchy"]
    assert sorted(c.name for c in player.hand) == ["Gold", "Gold", "Scheme"]


def test_artificer_override_spends_junk_first_then_useful_cards():
    # A strategy hook may deliberately pay more than the junk covers; the
    # extra card comes from the useful cards only after all junk is spent.
    state = _setup(["Artificer", "Scheme"])
    player = state.current_player
    scheme = get_card("Scheme")
    player.ai.choose_artificer_gain = lambda s, p, choices: next(
        c for c in choices if c.name == "Scheme"
    )
    player.hand = [get_card("Silver"), get_card("Copper"), get_card("Gold"), get_card("Estate")]
    player.deck = []

    artificer = get_card("Artificer")
    player.in_play.append(artificer)
    artificer.play_effect(state)

    assert player.deck and player.deck[-1].name == scheme.name
    assert sorted(c.name for c in player.discard) == ["Copper", "Estate", "Silver"]
    assert [c.name for c in player.hand] == ["Gold"]


def test_a_failed_knights_rule_covers_every_knight_in_the_action_fallback():
    from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

    strategy = EnhancedStrategy()
    strategy.action_priority = [
        PriorityRule("Knights", PriorityRule.turn_number(">", 999)),
    ]
    state = _setup(["Knights", "Village"])
    player = state.current_player
    knight = get_card("Sir Bailey")
    village = get_card("Village")
    player.hand = [knight]

    # GeneticAI drops the pass option during the main action phase, so a
    # Knight whose rule failed used to count as "unexpected" and was played.
    assert strategy.choose_action(state, player, [knight]) is None
    # Cards no rule mentions are still played by the fallback.
    assert strategy.choose_action(state, player, [knight, village]) is village
    # The same coverage applies to the Overlord target fallback.
    assert strategy.choose_overlord_target(state, player, [knight, village]) is village
