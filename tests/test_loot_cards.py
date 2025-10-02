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


def test_sword_attack_discards_low_value_cards_first():
    attacker = ChooseFirstActionAI()
    defender = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([attacker, defender], [get_card("Sword")])

    sword = get_card("Sword")
    gold = get_card("Gold")
    province = get_card("Province")
    silver = get_card("Silver")
    estate = get_card("Estate")
    copper = get_card("Copper")

    attacker_state, defender_state = state.players
    state.current_player_index = 0
    attacker_state.hand = [sword]
    defender_state.hand = [gold, province, silver, estate, copper]
    defender_state.discard = []

    sword.play_effect(state)

    assert len(defender_state.hand) == 4
    assert any(card.name == "Estate" for card in defender_state.discard)
    assert all(card.name != "Gold" for card in defender_state.discard)
    assert any(card.name == "Gold" for card in defender_state.hand)
