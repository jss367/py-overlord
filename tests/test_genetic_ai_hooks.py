from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class HookStrategy(EnhancedStrategy):
    def choose_watchtower_reaction(self, state, player, gained_card):
        return "topdeck"

    def choose_card_to_topdeck_for_clerk(self, state, player, choices):
        return choices[-1]

    def should_play_clerk_reaction(self, state, player, clerk=None):
        return False

    def choose_investment_mode(self, state, player, can_trash_treasure):
        return "trash"

    def choose_treasure_to_trash_for_investment(self, state, player, choices):
        return choices[-1]


def test_genetic_ai_delegates_card_specific_strategy_hooks():
    strategy = HookStrategy()
    ai = GeneticAI(strategy)
    player = PlayerState(ai)
    gained = get_card("City")
    choices = [get_card("Copper"), get_card("Silver")]

    assert ai.choose_watchtower_reaction(None, player, gained) == "topdeck"
    assert ai.choose_card_to_topdeck_for_clerk(None, player, choices).name == "Silver"
    assert ai.should_play_clerk_reaction(None, player, get_card("Clerk")) is False
    assert ai.choose_investment_mode(None, player, True) == "trash"
    assert ai.choose_treasure_to_trash_for_investment(None, player, choices).name == "Silver"


def test_enhanced_strategy_default_watchtower_policy_handles_common_gains():
    strategy = EnhancedStrategy()
    ai = GeneticAI(strategy)
    player = PlayerState(ai)

    assert ai.choose_watchtower_reaction(None, player, get_card("Curse")) == "trash"
    assert ai.choose_watchtower_reaction(None, player, get_card("Copper")) == "trash"
    assert ai.choose_watchtower_reaction(None, player, get_card("City")) == "topdeck"
    assert ai.choose_watchtower_reaction(None, player, get_card("Silver")) is None
    assert ai.choose_watchtower_reaction(None, player, get_card("Province")) is None


def test_enhanced_strategy_default_clerk_response_topdecks_junk():
    strategy = EnhancedStrategy()
    ai = GeneticAI(strategy)
    player = PlayerState(ai)
    choices = [get_card("Gold"), get_card("Estate"), get_card("Village")]

    assert ai.should_play_clerk_reaction(None, player, get_card("Clerk")) is True
    assert ai.choose_card_to_topdeck_for_clerk(None, player, choices).name == "Estate"


def test_enhanced_strategy_default_investment_policy_uses_treasure_variety():
    strategy = EnhancedStrategy()
    ai = GeneticAI(strategy)
    player = PlayerState(ai)
    player.hand = [get_card("Copper"), get_card("Silver"), get_card("Gold")]

    assert ai.choose_investment_mode(None, player, True) == "trash"
    assert ai.choose_treasure_to_trash_for_investment(None, player, list(player.hand)).name == "Copper"

    player.hand = [get_card("Copper"), get_card("Copper")]
    assert ai.choose_investment_mode(None, player, True) == "coin"


def test_enhanced_strategy_collection_bias_prefers_action_over_low_value_treasure():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver"), PriorityRule("City")]
    ai = GeneticAI(strategy)
    player = PlayerState(ai)
    player.collection_played = 1
    state = GameState([player])
    state.supply = {"Silver": 40, "City": 10}

    choice = ai.choose_buy(state, [get_card("Silver"), get_card("City")])

    assert choice.name == "City"
