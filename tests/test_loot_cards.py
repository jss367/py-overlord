from dominion.cards.registry import get_card
from dominion.cards.plunder import LOOT_CARD_NAMES
from dominion.cards.base_card import CardType
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import ChooseFirstActionAI, DummyAI, TrashFirstAI


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


def test_prize_goat_trash_and_decline():
    # Trashing scenario - AI trashes the first available card
    trashing_ai = TrashFirstAI()
    trashing_player = PlayerState(ai=trashing_ai)
    state_trash = GameState(players=[trashing_player])
    trashed_card = get_card("Copper")
    trashing_player.hand = [trashed_card]

    prize_goat = get_card("Prize Goat")
    prize_goat.play_effect(state_trash)

    assert trashed_card not in trashing_player.hand
    assert trashed_card in state_trash.trash

    # Decline scenario - AI chooses the None option to skip trashing
    class DeclineTrashAI(DummyAI):
        def __init__(self):
            super().__init__()
            self.last_choices = None

        def choose_card_to_trash(self, state, choices):
            self.last_choices = list(choices)
            return choices[-1] if choices else None

    decline_ai = DeclineTrashAI()
    decline_player = PlayerState(ai=decline_ai)
    state_decline = GameState(players=[decline_player])
    keep_card = get_card("Estate")
    decline_player.hand = [keep_card]

    prize_goat_skip = get_card("Prize Goat")
    prize_goat_skip.play_effect(state_decline)

    assert keep_card in decline_player.hand
    assert keep_card not in state_decline.trash
    assert decline_ai.last_choices is not None
    assert None in decline_ai.last_choices
