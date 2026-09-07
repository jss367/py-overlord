"""Rule regressions that materially affect the Kind Emperor strategy search."""

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.projects.registry import get_project
from dominion.prophecies.registry import get_prophecy
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from tests.utils import DummyAI


def setup(*names, ai=None):
    player = PlayerState(ai or DummyAI())
    state = GameState([player])
    state.log_callback = lambda *_: None
    state.setup_supply([get_card(n) for n in names])
    return state, player


def test_anvil_gains_during_play_and_cannot_gain_debt_card():
    class AnvilAI(DummyAI):
        def choose_anvil_gain(self, state, player, choices):
            assert "City Quarter" not in [c.name for c in choices]
            return next(c for c in choices if c.name == "Courier")

    state, player = setup("Anvil", "City Quarter", "Courier", ai=AnvilAI())
    copper = get_card("Copper")
    player.hand = [copper]
    anvil = get_card("Anvil")
    player.in_play = [anvil]
    anvil.on_play(state)
    assert copper in player.discard
    assert player.coins == 1
    assert state.supply["Courier"] == 9
    assert any(c.name == "Courier" for c in player.discard)
    state.handle_cleanup_phase()
    assert state.supply["Courier"] == 9


def test_courier_plays_previously_discarded_treasure_without_trashing():
    state, player = setup("Courier")
    copper, gold = get_card("Copper"), get_card("Gold")
    player.deck = [copper]
    player.discard = [gold]
    get_card("Courier").on_play(state)
    assert gold in player.in_play
    assert copper in player.discard
    assert player.coins == 4
    assert not state.trash


def test_courier_may_decline_to_play_the_discarded_card():
    class DeclineAI(DummyAI):
        def choose_courier_card(self, state, player, choices):
            return None

    state, player = setup("Courier", ai=DeclineAI())
    gold = get_card("Gold")
    player.deck = [gold]
    get_card("Courier").on_play(state)
    assert gold in player.discard
    assert player.coins == 1


def test_fortune_hunter_keeps_existing_top_card_out_of_reshuffle():
    state, player = setup("Fortune Hunter")
    gold = get_card("Gold")
    player.deck = [gold]
    player.discard = [get_card("Estate") for _ in range(8)]
    get_card("Fortune Hunter").on_play(state)
    assert gold in player.in_play
    assert player.coins == 5


def test_buried_treasure_gain_plays_now_but_resources_arrive_next_turn():
    state, player = setup("Buried Treasure")
    player.projects = [get_project("Guildhall")]
    card = get_card("Buried Treasure")
    buys = player.buys
    state.supply[card.name] -= 1
    state.gain_card(player, card)
    assert card in player.in_play and card in player.duration
    assert card not in player.discard
    assert player.coins == 0 and player.buys == buys
    assert player.coin_tokens == 1
    state.do_duration_phase()
    assert player.coins == 3 and player.buys == buys + 1
    assert card in player.in_play and card not in player.discard
    assert card not in player.duration
    state.handle_cleanup_phase()
    assert sum(c is card for c in player.hand + player.deck + player.discard) == 1


def test_buried_treasure_off_turn_gain_preserves_current_player():
    state, current = setup("Buried Treasure")
    other = PlayerState(DummyAI())
    state.players.append(other)
    card = get_card("Buried Treasure")
    state.gain_card(other, card)
    assert state.current_player is current
    assert state.turn_player is current
    assert card in other.duration and card not in current.duration


def test_mine_does_not_move_played_buried_treasure_back_to_hand():
    strategy = EnhancedStrategy()
    strategy.treasure_priority = [PriorityRule("Silver")]
    strategy.gain_priority = [PriorityRule("Buried Treasure")]
    state, player = setup("Mine", "Buried Treasure", ai=GeneticAI(strategy))
    player.hand = [get_card("Silver")]
    get_card("Mine").on_play(state)
    assert any(c.name == "Buried Treasure" for c in player.duration)
    assert not player.hand


def test_kind_emperor_can_gain_city_quarter_while_in_debt_without_more_debt():
    class EmperorStrategy(EnhancedStrategy):
        def choose_kind_emperor_gain(self, state, player, choices):
            return next(c for c in choices if c.name == "City Quarter")

    state, player = setup("City Quarter", ai=GeneticAI(EmperorStrategy()))
    player.debt = 2
    prophecy = get_prophecy("Kind Emperor")
    prophecy.on_turn_start(state, player)
    assert any(c.name == "City Quarter" for c in player.hand)
    assert player.debt == 2
    assert state.supply["City Quarter"] == 9


def test_coffers_pay_debt_before_a_purchase():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver")]
    state, player = setup("Imperial Envoy", ai=GeneticAI(strategy))
    player.coins = 1
    player.coin_tokens = 4
    player.debt = 2
    player.buys = 1
    state.handle_buy_phase()
    assert player.debt == 0
    assert player.coin_tokens == 0
    assert any(c.name == "Silver" for c in player.discard)


def test_mastermind_mine_upgrades_then_recycles_gold_for_three_coffers():
    from generated_strategies.mine_guildhall import MineGuildhall

    strategy = MineGuildhall()
    state, player = setup("Mine", "Mastermind", ai=GeneticAI(strategy))
    player.projects = [get_project("Guildhall")]
    mine = get_card("Mine")
    player.hand = [mine, get_card("Copper")]
    mastermind = get_card("Mastermind")
    player.in_play = [mastermind]
    player.duration = [mastermind]
    state.do_duration_phase()
    assert player.coin_tokens == 3
    assert [c.name for c in player.hand] == ["Gold"]
    assert strategy.mine_gains == {
        "Copper -> Silver": 1,
        "Silver -> Gold": 1,
        "Gold -> Gold": 1,
    }
    assert mine in player.in_play and mastermind in player.in_play


def test_mine_upgrade_selection_does_not_change_treasure_play_order():
    from generated_strategies.mine_guildhall import MineGuildhall

    strategy = MineGuildhall()
    state, player = setup("Mine", ai=GeneticAI(strategy))
    copper, gold = get_card("Copper"), get_card("Gold")
    player.hand = [copper, gold]
    assert player.ai.choose_treasure(state, player.hand) is gold
    get_card("Mine").on_play(state)
    assert copper in state.trash
    assert gold in player.hand
    assert any(c.name == "Silver" for c in player.hand)
