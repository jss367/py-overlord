from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


class TricksterTestAI(ChooseFirstActionAI):
    def choose_action(self, state, choices):
        for card in choices:
            if card is not None:
                return card
        return None

    def choose_treasure(self, state, choices):
        for card in choices:
            if card is not None:
                return card
        return None

    def should_set_aside_trickster_treasure(self, state, player, treasure):
        return treasure.name == "Copper"


def test_trickster_sets_aside_treasure_and_returns_it():
    ai = TricksterTestAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Trickster")])
    player = state.players[0]

    trickster = get_card("Trickster")
    prized_copper = get_card("Copper")
    silver = get_card("Silver")

    player.hand = [trickster, prized_copper, silver]
    player.deck = [get_card("Estate") for _ in range(5)]
    player.discard = []

    state.phase = "action"
    state.handle_action_phase()
    assert player.trickster_triggers_available == 1

    state.handle_treasure_phase()
    state.handle_buy_phase()
    state.handle_cleanup_phase()

    assert any(card is prized_copper for card in player.hand)
    assert not any(card is prized_copper for card in player.discard)
    assert any(card.name == "Silver" for card in player.discard)
    assert player.trickster_triggers_available == 0
