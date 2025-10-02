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


def test_jewels_returns_to_bottom_of_deck_after_duration():
    state = GameState(players=[])
    state.initialize_game([ChooseFirstActionAI()], [get_card("Village")])

    player = state.players[0]
    jewels = get_card("Jewels")
    existing = [get_card("Copper"), get_card("Estate")]

    player.deck = existing.copy()
    player.duration = [jewels]

    jewels.on_duration(state)

    assert jewels not in player.duration
    assert player.deck == existing + [jewels]
