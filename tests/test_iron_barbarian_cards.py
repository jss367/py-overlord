from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.projects import Innovation
from tests.utils import DummyAI


def make_state(num_players=1, kingdom=None, projects=None):
    ais = [DummyAI() for _ in range(num_players)]
    state = GameState(players=[])
    kingdom_cards = kingdom or [get_card("Village")]
    state.initialize_game(ais, kingdom_cards, projects=projects)
    return state


def test_bridge_reduces_cost():
    state = make_state()
    player = state.players[0]
    bridge = get_card("Bridge")
    bridge.on_play(state)
    silver_cost = state.get_card_cost(player, get_card("Silver"))
    assert silver_cost == 2


def test_marauder_gives_spoils_and_ruins():
    state = make_state(num_players=2, kingdom=[get_card("Marauder")])
    player, opponent = state.players
    marauder = get_card("Marauder")
    spoils_before = state.supply["Spoils"]
    ruins_before = state.supply["Ruins"]

    marauder.on_play(state)

    assert any(card.name == "Spoils" for card in player.discard)
    # The opponent gains the top of the Ruins pile, which is one of the five
    # Ruins variants (Abandoned Mine, Ruined Library, Ruined Market, Ruined
    # Village, Survivors). Check that a Ruins-typed card was gained.
    assert any(card.is_ruins for card in opponent.discard)
    assert state.supply["Spoils"] == spoils_before - 1
    assert state.supply["Ruins"] == ruins_before - 1


def test_innovation_plays_first_gained_action():
    state = make_state(projects=[Innovation()])
    player = state.players[0]
    player.projects.append(Innovation())
    bridge = get_card("Bridge")
    state.supply.setdefault("Bridge", 10)
    state.gain_card(player, bridge)
    assert bridge in player.in_play
    assert bridge not in player.discard
    assert player.innovation_used


def test_tragic_hero_trashes_and_gains_treasure():
    state = make_state()
    player = state.players[0]
    tragic = get_card("Tragic Hero")
    player.hand = [tragic] + [get_card("Copper") for _ in range(7)]
    player.deck = [get_card("Copper") for _ in range(3)]
    player.actions = 1
    player.hand.remove(tragic)
    player.in_play.append(tragic)
    tragic.on_play(state)
    assert any(card.name == "Gold" for card in player.hand)
    assert tragic in state.trash
    assert tragic not in player.in_play


def test_giant_flips_token_and_attacks():
    state = make_state(num_players=2, kingdom=[get_card("Giant")])
    player, opponent = state.players
    opponent.deck = [get_card("Copper")]
    opponent.discard = []
    player.coins = 0
    player.journey_token_face_up = True
    giant = get_card("Giant")
    giant.on_play(state)
    assert player.coins == 1
    assert not player.journey_token_face_up
    giant.on_play(state)
    assert player.coins == 6
    assert player.journey_token_face_up
    assert any(card.name == "Curse" for card in opponent.discard)


def test_barbarian_trashes_and_replaces():
    state = make_state(num_players=2, kingdom=[get_card("Barbarian")])
    player, opponent = state.players
    opponent.deck = [get_card("Silver")]
    opponent.discard = []
    barbarian = get_card("Barbarian")
    barbarian.on_play(state)
    assert any(card.name == "Copper" for card in opponent.discard)
    assert any(card.name == "Silver" for card in state.trash)


def test_barbarian_does_not_curse_without_valid_replacement():
    state = make_state(num_players=2, kingdom=[get_card("Barbarian")])
    player, opponent = state.players
    opponent.deck = [get_card("Gold")]
    opponent.discard = []
    barbarian = get_card("Barbarian")

    for name in ["Copper", "Silver", "Gold"]:
        state.supply[name] = 0
    state.supply["Curse"] = 10

    barbarian.on_play(state)

    assert not opponent.discard
    assert state.supply["Curse"] == 10
    assert any(card.name == "Gold" for card in state.trash)


def test_barbarian_offers_cheaper_potion_cost_replacement():
    """Trashing Familiar ($3P) may be replaced by Scrying Pool ($2P): cheaper
    means no cost component higher and at least one lower."""
    state = make_state(
        num_players=2,
        kingdom=[get_card("Barbarian"), get_card("Familiar"), get_card("Scrying Pool")],
    )
    player, opponent = state.players
    opponent.deck = [get_card("Familiar")]
    opponent.discard = []
    offered = []

    class _PoolAI(DummyAI):
        def choose_buy(self, state, choices):
            offered.extend(c.name for c in choices if c is not None)
            return next(c for c in choices if c is not None and c.name == "Scrying Pool")

    opponent.ai = _PoolAI()
    get_card("Barbarian").on_play(state)
    assert "Scrying Pool" in offered
    assert "Familiar" not in offered
    assert any(c.name == "Scrying Pool" for c in opponent.discard)
    assert any(c.name == "Familiar" for c in state.trash)


def test_barbarian_replacement_is_chosen_against_the_victim_deck():
    """The attacked player's gain rules must see the attacked player as the
    current player, not the attacker (GeneticAI.choose_buy evaluates its
    strategy against ``state.current_player``)."""
    from dominion.ai.genetic_ai import GeneticAI
    from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

    state = make_state(num_players=2, kingdom=[get_card("Barbarian")])
    player, opponent = state.players

    victim = EnhancedStrategy()
    victim.name = "victim"
    victim.gain_priority = [
        PriorityRule("Silver", PriorityRule.max_in_deck("Silver", 1)),
        PriorityRule("Copper"),
    ]
    opponent.ai = GeneticAI(victim)

    # The victim already owns a Silver, so its rule says "no more Silver";
    # the attacker owns none, so the same rule evaluated against the
    # attacker's deck would wrongly pick Silver.
    opponent.deck = [get_card("Gold")]
    opponent.discard = [get_card("Silver")]
    opponent.hand = []
    assert player.count_in_deck("Silver") == 0
    assert opponent.count_in_deck("Silver") == 1

    get_card("Barbarian").on_play(state)

    assert state.current_player is player
    assert any(c.name == "Gold" for c in state.trash)
    assert [c.name for c in opponent.discard] == ["Silver", "Copper"]
