from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _state_with_strategy(strategy: EnhancedStrategy) -> tuple[GameState, GeneticAI]:
    ai = GeneticAI(strategy)
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.log_callback = lambda *args, **kwargs: None
    return state, ai


def test_choose_buy_can_decline_when_none_offered_and_no_gain_priority_matches():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Gold")]
    state, ai = _state_with_strategy(strategy)

    choice = ai.choose_buy(state, [get_card("Silver"), None])

    assert choice is None


def test_choose_action_can_decline_when_none_offered_and_no_action_priority_matches():
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Smithy")]
    state, ai = _state_with_strategy(strategy)

    choice = ai.choose_action(state, [get_card("Village"), None])

    assert choice is None


def test_priority_matches_still_win_when_none_is_present():
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Village")]
    strategy.gain_priority = [PriorityRule("Silver")]
    state, ai = _state_with_strategy(strategy)

    action_choice = ai.choose_action(state, [get_card("Smithy"), None, get_card("Village")])
    buy_choice = ai.choose_buy(state, [get_card("Copper"), None, get_card("Silver")])

    assert action_choice is not None
    assert action_choice.name == "Village"
    assert buy_choice is not None
    assert buy_choice.name == "Silver"
