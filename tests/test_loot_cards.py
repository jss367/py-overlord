from dominion.cards.registry import get_card
from dominion.cards.plunder import LOOT_CARD_NAMES
from dominion.cards.base_card import CardType
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


def test_loot_cards_all_defined():
    assert len(LOOT_CARD_NAMES) == 15
    for name in LOOT_CARD_NAMES:
        card = get_card(name)
        assert CardType.TREASURE in card.types


def test_sword_and_shield_types():
    shield = get_card("Shield")
    assert CardType.REACTION in shield.types

    sword = get_card("Sword")
    assert CardType.ATTACK in sword.types


def test_shield_blocks_witch_attack():
    attacker = ChooseFirstActionAI()
    defender = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([attacker, defender], [get_card("Witch")])

    p1, p2 = state.players
    p1.hand = [get_card("Witch")]
    p2.hand = [get_card("Shield")]
    state.phase = "action"
    state.handle_action_phase()

    assert not any(c.name == "Curse" for c in p2.discard)


def test_puzzle_box_sets_aside_non_action_and_returns_next_turn():
    class DelayCopperAI(ChooseFirstActionAI):
        def __init__(self):
            super().__init__()
            self._puzzle_played = False

        def choose_treasure(self, state, choices):
            for card in choices:
                if card is not None and card.name == "Puzzle Box" and not self._puzzle_played:
                    self._puzzle_played = True
                    return card
            return None

        def choose_card_to_delay(self, state, player, choices):
            for card in choices:
                if card.name == "Copper":
                    return card
            return None

    ai = DelayCopperAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")])

    player = state.current_player
    puzzle_box = get_card("Puzzle Box")
    copper = get_card("Copper")

    state.phase = "start"
    state.handle_start_phase()

    player.hand = [puzzle_box, copper]
    player.deck = [get_card("Estate") for _ in range(5)]
    player.discard = []

    state.phase = "treasure"
    state.handle_treasure_phase()

    assert copper not in player.hand
    assert copper in player.delayed_cards

    state.handle_buy_phase()
    state.handle_cleanup_phase()

    assert copper not in player.hand
    assert copper in player.delayed_cards

    state.handle_start_phase()

    assert copper in player.hand
    assert copper not in player.delayed_cards
