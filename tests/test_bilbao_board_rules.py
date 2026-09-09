"""Rule regressions that materially affect the Bilbao board strategy search.

Kingdom: Fool's Gold (Rich), Grotto, Shaman, Anvil, Hermit, Sheepdog, Feodum,
Wandering Minstrel, Wheelwright, Raider (``boards/bilbao.txt``).
"""

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from tests.utils import DummyAI

BILBAO = [
    "Fool's Gold",
    "Grotto",
    "Shaman",
    "Anvil",
    "Hermit",
    "Sheepdog",
    "Feodum",
    "Wandering Minstrel",
    "Wheelwright",
    "Raider",
]


def _strategy(gain=(), trash=()):
    strat = EnhancedStrategy()
    strat.name = "bilbao-test"
    strat.gain_priority = [PriorityRule(name) for name in gain]
    strat.trash_priority = [PriorityRule(name) for name in trash]
    return strat


def _game(ais=None, num_players=2, traits=None):
    ais = ais or [DummyAI() for _ in range(num_players)]
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    state.initialize_game(ais, [get_card(n) for n in BILBAO])
    if traits:
        from dominion.traits.registry import apply_trait

        for card_name, trait_name in traits.items():
            apply_trait(state, trait_name, card_name)
    for p in state.players:
        p.hand, p.deck, p.discard, p.in_play, p.duration = [], [], [], [], []
        p.actions, p.buys, p.coins = 1, 1, 0
    return state


def test_board_file_loads_with_rich_on_fools_gold():
    board = load_board("boards/bilbao.txt")
    assert board.kingdom_cards == BILBAO
    assert board.traits == {"Fool's Gold": "Rich"}


# --- Shaman -----------------------------------------------------------------


def test_shaman_is_a_plain_cantrip_not_a_duration():
    shaman = get_card("Shaman")
    assert shaman.is_action and not shaman.is_duration
    assert shaman.stats.actions == 1 and shaman.stats.coins == 1


def test_shaman_rule_gains_from_trash_for_every_player_without_owning_one():
    """In games using Shaman every player gains from the trash at the start of
    their turn, from turn one, even if nobody bought a Shaman."""
    state = _game()
    p0, p1 = state.players
    assert state.game_uses_shaman()
    state.trash.append(get_card("Silver"))
    state._handle_shaman_start_of_turn(p1)
    assert any(c.name == "Silver" for c in p1.discard)
    assert not state.trash
    # Nothing left for the next player.
    state._handle_shaman_start_of_turn(p0)
    assert not p0.discard


def test_shaman_rule_is_inactive_without_shaman_in_the_game():
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    state.initialize_game([DummyAI(), DummyAI()], [get_card("Village")])
    assert not state.game_uses_shaman()
    state.trash.append(get_card("Silver"))
    state._handle_shaman_start_of_turn(state.players[0])
    assert len(state.trash) == 1


def test_shaman_rule_only_offers_cards_costing_up_to_six():
    state = _game()
    p0 = state.players[0]
    province = get_card("Province")
    gold = get_card("Gold")
    state.trash.extend([province, gold])
    state._handle_shaman_start_of_turn(p0)
    assert gold in p0.discard
    assert state.trash == [province]


def test_shaman_gain_is_mandatory_even_when_only_junk_is_trashed():
    """Trashing an Estate hands it to the next player: the gain is forced."""
    state = _game()
    p1 = state.players[1]
    estate = get_card("Estate")
    state.trash.append(estate)
    state._handle_shaman_start_of_turn(p1)
    assert estate in p1.discard
    assert not state.trash


def test_shaman_default_pick_prefers_least_harmful_card():
    state = _game()
    p0 = state.players[0]
    curse, estate, copper = get_card("Curse"), get_card("Estate"), get_card("Copper")
    state.trash.extend([curse, estate, copper])
    state._handle_shaman_start_of_turn(p0)
    assert copper in p0.discard
    assert curse in state.trash and estate in state.trash


def test_shaman_gain_follows_the_strategy_gain_list():
    strat = _strategy(gain=["Sheepdog", "Gold"])
    state = _game(ais=[GeneticAI(strat), DummyAI()])
    p0 = state.players[0]
    gold, sheepdog = get_card("Gold"), get_card("Sheepdog")
    state.trash.extend([gold, sheepdog])
    state._handle_shaman_start_of_turn(p0)
    assert sheepdog in p0.discard
    assert state.trash == [gold]


def test_shaman_rule_stays_active_after_buying_it_out_of_black_market():
    """Shaman "in the game" is latched at setup. Buying the only copy out of
    the Black Market deck drops its name from ``black_market_deck``; the
    game-wide rule must keep applying for the rest of the game."""
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    state.initialize_game([DummyAI(), DummyAI()], [get_card("Black Market")])
    assert "Shaman" not in state.supply
    assert "Shaman" in state.black_market_deck
    assert state.game_uses_shaman()

    # What BlackMarket.play_effect does when the Shaman is bought.
    state.black_market_deck.remove("Shaman")
    assert state.game_uses_shaman()
    p0 = state.players[0]
    state.trash.append(get_card("Silver"))
    state._handle_shaman_start_of_turn(p0)
    assert any(c.name == "Silver" for c in p0.discard)
    assert not state.trash


def test_shaman_latch_resets_between_games_on_same_state():
    state = _game()
    assert state.game_uses_shaman()
    state.initialize_game([DummyAI(), DummyAI()], [get_card("Village")])
    assert not state.game_uses_shaman()


class _RevealTraderAI(DummyAI):
    def should_reveal_trader(self, state, player, gained_card, *, to_deck):
        return True


def test_shaman_gain_replaced_by_trader_leaves_card_in_trash():
    """Revealing Trader swaps the Shaman gain for a Silver; the chosen card
    was never gained, so it must remain in the trash."""
    state = _game(ais=[_RevealTraderAI(), DummyAI()])
    p0 = state.players[0]
    p0.hand = [get_card("Trader")]
    gold = get_card("Gold")
    state.trash.append(gold)
    silver_before = state.supply["Silver"]

    state._handle_shaman_start_of_turn(p0)

    assert [c.name for c in p0.discard] == ["Silver"]
    assert state.trash == [gold]
    assert state.supply["Silver"] == silver_before - 1


def test_shaman_rule_fires_during_a_real_turn_start():
    state = _game()
    p0 = state.players[0]
    p0.deck = [get_card("Copper") for _ in range(5)]
    state.current_player_index = 0
    state.trash.append(get_card("Silver"))
    state.handle_start_phase()
    assert any(c.name == "Silver" for c in p0.discard)
    assert not state.trash


def test_shaman_play_trashes_via_strategy_trash_list():
    strat = _strategy(trash=["Estate"])
    state = _game(ais=[GeneticAI(strat), DummyAI()])
    p0 = state.players[0]
    state.current_player_index = 0
    estate, copper = get_card("Estate"), get_card("Copper")
    p0.hand = [estate, copper]
    shaman = get_card("Shaman")
    p0.in_play.append(shaman)
    shaman.on_play(state)
    assert estate in state.trash
    assert p0.hand == [copper]
    assert p0.coins == 1
    # +1 Action on top of the turn's starting Action (on_play does not spend one).
    assert p0.actions == 2


def test_hermit_trashing_feodum_gains_silvers_then_opponent_recovers_feodum():
    strat = _strategy(trash=["Feodum"], gain=["Silver"])
    state = _game(ais=[GeneticAI(strat), DummyAI()])
    p0, p1 = state.players
    state.current_player_index = 0
    feodum = get_card("Feodum")
    p0.discard = [feodum]
    hermit = get_card("Hermit")
    p0.in_play.append(hermit)
    hermit.on_play(state)
    assert feodum in state.trash
    # Feodum's on-trash: 3 Silvers, plus Hermit's own gain (Silver by list).
    assert sum(1 for c in p0.discard if c.name == "Silver") == 4
    # The opponent's turn starts: Feodum is the only card in the trash, so
    # the Shaman rule forces them to take it.
    state._handle_shaman_start_of_turn(p1)
    assert feodum in p1.discard
    assert not state.trash


# --- Hermit -----------------------------------------------------------------


def test_hermit_exchange_returns_hermit_to_pile_not_trash():
    state = _game()
    p0 = state.players[0]
    state.current_player_index = 0
    hermit = get_card("Hermit")
    state.supply["Hermit"] -= 1
    p0.in_play.append(hermit)
    p0.cards_gained_this_buy_phase = 0
    state._handle_buy_phase_end(p0)
    assert hermit not in state.trash
    assert state.supply["Hermit"] == 10
    assert state.supply["Madman"] == 9
    assert any(c.name == "Madman" for c in p0.discard)
    # A trashed-Hermit would have been recoverable by the Shaman rule; it is not.
    state._handle_shaman_start_of_turn(state.players[1])
    assert not state.players[1].discard


def test_hermit_gain_follows_the_strategy_gain_list():
    strat = _strategy(gain=["Silver", "Sheepdog"])
    state = _game(ais=[GeneticAI(strat), DummyAI()])
    p0 = state.players[0]
    state.current_player_index = 0
    hermit = get_card("Hermit")
    p0.in_play.append(hermit)
    hermit.on_play(state)
    assert [c.name for c in p0.discard] == ["Silver"]


# --- Raider -----------------------------------------------------------------


def test_raider_ignores_opponent_with_four_cards_in_hand():
    state = _game()
    p0, p1 = state.players
    state.current_player_index = 0
    raider = get_card("Raider")
    p0.in_play = [raider, get_card("Shaman")]
    p1.hand = [get_card("Shaman")] + [get_card("Copper") for _ in range(3)]
    raider.on_play(state)
    assert not p1.discard
    assert len(p1.hand) == 4


def test_raider_hits_opponent_with_five_cards_in_hand():
    state = _game()
    p0, p1 = state.players
    state.current_player_index = 0
    raider = get_card("Raider")
    p0.in_play = [raider, get_card("Shaman")]
    p1.hand = [get_card("Shaman")] + [get_card("Copper") for _ in range(4)]
    raider.on_play(state)
    assert [c.name for c in p1.discard] == ["Shaman"]
    assert len(p1.hand) == 4


# --- Fool's Gold + Rich -----------------------------------------------------


def test_rich_fools_gold_gain_also_gains_a_silver():
    state = _game(traits={"Fool's Gold": "Rich"})
    p0 = state.players[0]
    state.supply["Fool's Gold"] -= 1
    state.gain_card(p0, get_card("Fool's Gold"))
    names = sorted(c.name for c in p0.discard)
    assert names == ["Fool's Gold", "Silver"]


def test_fools_gold_reaction_uses_the_ai_hook():
    class NeverReact(DummyAI):
        def should_trash_fools_gold_for_gold(self, state, player):
            return False

    class AlwaysReact(DummyAI):
        def should_trash_fools_gold_for_gold(self, state, player):
            return True

    for ai_cls, expect_gold in ((NeverReact, False), (AlwaysReact, True)):
        state = _game(ais=[DummyAI(), ai_cls()])
        p0, p1 = state.players
        state.current_player_index = 0
        fg = get_card("Fool's Gold")
        p1.hand = [fg]
        p1.deck = [get_card("Copper")]
        state.supply["Province"] -= 1
        state.gain_card(p0, get_card("Province"))
        assert (fg in state.trash) is expect_gold
        assert (p1.deck[-1].name == "Gold") is expect_gold


def test_fools_gold_second_copy_is_worth_four():
    state = _game()
    p0 = state.players[0]
    state.current_player_index = 0
    for _ in range(2):
        fg = get_card("Fool's Gold")
        p0.in_play.append(fg)
        fg.on_play(state)
    assert p0.coins == 5


# --- Wheelwright / Grotto ---------------------------------------------------


def test_wheelwright_keeps_estate_when_strategy_wants_no_cheap_action():
    strat = _strategy(gain=["Gold"])
    state = _game(ais=[GeneticAI(strat), DummyAI()])
    p0 = state.players[0]
    state.current_player_index = 0
    estate = get_card("Estate")
    p0.hand = [estate, get_card("Copper")]
    p0.deck = [get_card("Silver")]
    ww = get_card("Wheelwright")
    p0.in_play.append(ww)
    ww.on_play(state)
    assert estate in p0.hand
    assert not p0.discard


def test_wheelwright_discards_estate_to_gain_wanted_two_cost_action():
    strat = _strategy(gain=["Shaman"])
    state = _game(ais=[GeneticAI(strat), DummyAI()])
    p0 = state.players[0]
    state.current_player_index = 0
    estate = get_card("Estate")
    p0.hand = [estate, get_card("Copper")]
    p0.deck = [get_card("Silver")]
    ww = get_card("Wheelwright")
    p0.in_play.append(ww)
    ww.on_play(state)
    assert estate in p0.discard
    assert any(c.name == "Shaman" for c in p0.discard)
    assert state.supply["Shaman"] == 9


def test_grotto_set_aside_follows_strategy_hook():
    class Strat(EnhancedStrategy):
        def choose_grotto_set_aside(self, state, player, hand):
            return [c for c in hand if c.name == "Copper"][:4]

    strat = Strat()
    strat.name = "grotto-test"
    state = _game(ais=[GeneticAI(strat), DummyAI()])
    p0 = state.players[0]
    state.current_player_index = 0
    p0.hand = [get_card("Copper") for _ in range(5)] + [get_card("Estate")]
    grotto = get_card("Grotto")
    p0.in_play.append(grotto)
    grotto.on_play(state)
    assert len(grotto.set_aside) == 4
    assert sorted(c.name for c in p0.hand) == ["Copper", "Estate"]


# --- Fool's Gold reaction under Shaman's rule ------------------------------


def test_fools_gold_reaction_fires_once_per_trigger_with_shaman():
    """Shaman returns one card per turn, so only one copy is worth trashing."""
    state = _game()
    p0, p1 = state.players
    state.current_player_index = 0
    fgs = [get_card("Fool's Gold"), get_card("Fool's Gold")]
    p1.hand = list(fgs)
    p1.deck = [get_card("Copper")]
    state.supply["Province"] -= 1
    state.gain_card(p0, get_card("Province"))
    assert sum(1 for c in state.trash if c.name == "Fool's Gold") == 1
    assert sum(1 for c in p1.hand if c.name == "Fool's Gold") == 1
    assert p1.deck[-1].name == "Gold"


def test_fools_gold_reaction_declined_when_trash_already_holds_one():
    state = _game()
    p0, p1 = state.players
    state.current_player_index = 0
    state.trash.append(get_card("Fool's Gold"))
    p1.hand = [get_card("Fool's Gold")]
    p1.deck = [get_card("Copper")]
    state.supply["Province"] -= 1
    state.gain_card(p0, get_card("Province"))
    assert len(p1.hand) == 1
    assert p1.deck[-1].name == "Copper"


def test_fools_gold_reaction_declined_when_another_player_acts_first():
    state = _game(num_players=3)
    p0, p1, p2 = state.players
    state.current_player_index = 0
    for p in (p1, p2):
        p.hand = [get_card("Fool's Gold")]
        p.deck = [get_card("Copper")]
    state.supply["Province"] -= 1
    state.gain_card(p0, get_card("Province"))
    # p1 acts next and reacts; p2 would lose its copy to p1, so it keeps it.
    assert p1.deck[-1].name == "Gold"
    assert p2.deck[-1].name == "Copper"
    assert len(p2.hand) == 1


# --- Best Found Anvil guard ------------------------------------------------


def test_best_found_anvil_guard_accounts_for_silver_discard():
    from generated_strategies.bilbao_best_found import BilbaoBestFound

    strat = BilbaoBestFound()
    state = _game(ais=[GeneticAI(strat), DummyAI()])
    p0 = state.players[0]
    state.current_player_index = 0
    anvil = get_card("Anvil")
    # Anvil in play ($1 already counted), hand Gold + Silver + Silver + Anvil = $9;
    # the only discard is a Silver, which would drop the hand to $7.
    p0.in_play = [anvil]
    p0.coins = 1
    p0.hand = [get_card("Gold"), get_card("Silver"), get_card("Silver"), get_card("Anvil")]
    choices = [get_card("Feodum"), get_card("Fool's Gold")]
    assert strat.choose_anvil_gain(state, p0, choices) is None
    # With a Copper available the discard costs $1 and the gain proceeds.
    p0.hand.append(get_card("Copper"))
    assert strat.choose_anvil_gain(state, p0, choices) is not None
