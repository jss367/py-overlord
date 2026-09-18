"""Rules that materially affect the Stables / Ninja / Museum board search."""
from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.landmarks.registry import get_landmark
from dominion.strategy.strategies.stables_ninja_museum import KINGDOM, StablesNinjaMuseum


def make_state():
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    state.initialize_game([GeneticAI(StablesNinjaMuseum()) for _ in range(2)],
                          [get_card(n) for n in (*KINGDOM, "Platinum", "Colony")],
                          events=[get_event("Credit")], landmarks=[get_landmark("Museum")])
    p = state.current_player
    p.hand, p.deck, p.discard, p.in_play = [], [], [], []
    p.coins, p.buys, p.actions = 0, 1, 10
    return state, p


def play(state, player, name):
    card = get_card(name)
    player.in_play.append(card)
    card.on_play(state)
    return card


def test_pendant_counts_names_at_play_time_and_can_fund_a_purchase():
    state, p = make_state()
    p.hand = [get_card(n) for n in ("Copper", "Silver", "Gold", "Pendant", "Pendant")]
    state.handle_treasure_phase()
    # Copper + Silver + Gold = 6; each Pendant sees four names, including itself.
    assert p.coins == 14
    p.turns_taken = 10
    state.handle_buy_phase()
    assert p.count("Colony") == 1


def test_pendant_does_not_count_treasures_played_after_it():
    state, p = make_state()
    play(state, p, "Pendant")
    assert p.coins == 1
    play(state, p, "Gold")
    assert p.coins == 4


def test_figurine_draws_then_discards_an_action_for_money_and_buy():
    state, p = make_state()
    p.deck = [get_card("Gold"), get_card("Catapult")]
    play(state, p, "Figurine")
    assert [c.name for c in p.hand] == ["Gold"]
    assert [c.name for c in p.discard] == ["Catapult"]
    assert (p.coins, p.buys, p.actions) == (1, 2, 10)


def test_figurine_without_an_action_only_draws():
    state, p = make_state()
    p.deck = [get_card("Gold"), get_card("Silver")]
    play(state, p, "Figurine")
    assert len(p.hand) == 2
    assert (p.coins, p.buys) == (0, 1)


def test_watchtower_does_not_draw_if_hand_already_contains_six():
    state, p = make_state()
    p.hand = [get_card("Copper") for _ in range(6)]
    p.deck = [get_card("Gold") for _ in range(5)]
    play(state, p, "Watchtower")
    assert len(p.hand) == 6 and len(p.deck) == 5


def test_harbor_villages_do_not_save_triggers_past_the_next_action():
    state, p = make_state()
    p.hand = [get_card(n) for n in ("Harbor Village", "Harbor Village", "Conclave")]
    state.handle_action_phase()
    assert p.coins == 3
    assert p.harbor_village_pending == 0


def test_conclave_played_harbor_village_bonuses_the_next_action():
    state, p = make_state()
    p.hand = [get_card("Harbor Village")]
    play(state, p, "Conclave")
    assert p.harbor_village_pending == 1
    p.hand = [get_card("Conclave")]
    state.handle_action_phase()
    assert p.coins == 5


def test_credit_cannot_gain_platinum_or_victory_cards():
    state, p = make_state()
    class CaptureAI:
        def choose_buy(self, state, choices):
            names = {c.name for c in choices if c is not None}
            assert not names & {"Colony", "Province", "Platinum"}
            return next(c for c in choices if c is not None and c.name == "Stables")
    p.ai = CaptureAI()
    get_event("Credit").on_buy(state, p)
    assert p.count("Stables") == 1 and p.debt == 5


def test_museum_counts_a_curse_as_one_net_point_and_split_pile_names_separately():
    state, p = make_state()
    p.hand = [get_card(n) for n in ("Catapult", "Rocks", "Curse")]
    assert p.get_victory_points() == 5


def test_rocks_trash_gains_silver_to_hand_and_buy_gain_topdecks_it():
    state, p = make_state()
    state.phase = "action"
    state.trash_card(p, get_card("Rocks"))
    assert [c.name for c in p.hand] == ["Silver"]
    state.phase = "buy"
    state.gain_card(p, get_card("Rocks"))
    assert p.deck[-1].name == "Silver"
    assert not get_card("Rocks").is_victory


def test_figurine_discard_is_optional():
    state, p = make_state()
    p.hand = [get_card("Watchtower")]
    class PreserveWatchtower(StablesNinjaMuseum):
        def choose_action_to_discard_for_figurine(self, state, player, choices):
            assert [c.name for c in choices] == ["Watchtower"]
            self.asked = True
            return None
    strategy = PreserveWatchtower()
    p.ai = GeneticAI(strategy)
    play(state, p, "Figurine")
    assert [c.name for c in p.hand] == ["Watchtower"]
    assert (p.coins, p.buys) == (0, 1)
    assert strategy.asked


def test_rocks_gained_on_an_opponents_buy_phase_gains_silver_to_hand():
    state, p = make_state()
    opponent = state.players[1]
    opponent.hand = []
    state.phase = "buy"
    state.gain_card(opponent, get_card("Rocks"))
    assert [c.name for c in opponent.hand] == ["Silver"]


def test_figurine_strategy_can_choose_a_more_expensive_action():
    state, p = make_state()
    class PreserveWatchtower(StablesNinjaMuseum):
        def choose_action_to_discard_for_figurine(self, state, player, choices):
            return next(c for c in choices if c.name == "Ninja")
    p.ai = GeneticAI(PreserveWatchtower())
    p.hand = [get_card("Watchtower"), get_card("Ninja")]
    play(state, p, "Figurine")
    assert [c.name for c in p.hand] == ["Watchtower"]
    assert [c.name for c in p.discard] == ["Ninja"]
    assert (p.coins, p.buys) == (1, 2)


def test_strategy_declares_the_museum_landmark_it_scores_on():
    """Nothing gains or plays Museum, so only an explicit declaration carries it.

    Without this the board search's own kingdom loses its Landmark when the
    strategy is played outside the search script, and the catalog cannot show
    that anything uses Museum at all.
    """

    from dominion.simulation.strategy_battle import StrategyBattle, landscape_names

    battle = StrategyBattle()
    try:
        refs = battle._split_board_references(
            battle._extract_cards_from_strategy(StablesNinjaMuseum())
        )
    finally:
        battle.close()

    assert "Museum" in refs.landmarks
    assert "Museum" in landscape_names(refs)
