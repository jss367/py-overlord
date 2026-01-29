"""Encodes Dominion game state into numpy arrays for RL."""

import numpy as np
from dominion.game.game_state import GameState
from dominion.cards.registry import get_card


# Phase 1 fixed kingdom: simple engine cards
PHASE1_KINGDOM = ["Village", "Smithy", "Market", "Laboratory"]

# All cards we need to track (base + kingdom)
BASE_CARDS = ["Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse"]


class StateEncoder:
    """Encodes game state into a flat numpy vector.

    Encoding includes:
    - Current resources (actions, buys, coins) - 3 values
    - Turn number (normalized) - 1 value
    - Phase (one-hot: action, treasure, buy) - 3 values
    - Hand card counts (one per card type) - N values
    - Deck size (normalized) - 1 value
    - Discard size (normalized) - 1 value
    - Supply counts (one per pile) - M values
    - Opponent hand size, deck size - 2 values
    """

    def __init__(self, kingdom_cards: list[str]):
        """Initialize encoder with the kingdom card names."""
        self.kingdom_cards = list(kingdom_cards)
        self.all_cards = BASE_CARDS + self.kingdom_cards
        self.card_to_idx = {name: i for i, name in enumerate(self.all_cards)}

        # Calculate observation size
        # Resources: actions, buys, coins = 3
        # Turn number = 1
        # Phase one-hot = 3
        # Hand counts = len(all_cards)
        # Deck size, discard size = 2
        # Supply counts = len(all_cards)
        # Opponent info = 2
        self._obs_size = 3 + 1 + 3 + len(self.all_cards) + 2 + len(self.all_cards) + 2

    @property
    def observation_size(self) -> int:
        """Size of the observation vector."""
        return self._obs_size

    def encode(self, game_state: GameState, player_index: int) -> np.ndarray:
        """Encode game state from perspective of player_index."""
        obs = np.zeros(self._obs_size, dtype=np.float32)
        idx = 0

        player = game_state.players[player_index]
        opponent_index = 1 - player_index
        opponent = game_state.players[opponent_index]

        # Resources (normalized to reasonable ranges)
        obs[idx] = player.actions / 10.0  # Usually 0-5
        idx += 1
        obs[idx] = player.buys / 5.0  # Usually 1-3
        idx += 1
        obs[idx] = player.coins / 20.0  # Usually 0-15
        idx += 1

        # Turn number (normalized, games usually 15-30 turns)
        obs[idx] = game_state.turn_number / 50.0
        idx += 1

        # Phase one-hot
        phase_map = {"action": 0, "treasure": 1, "buy": 2}
        phase_idx = phase_map.get(game_state.phase, 0)
        obs[idx + phase_idx] = 1.0
        idx += 3

        # Hand card counts
        hand_counts = self._count_cards(player.hand)
        for card_name in self.all_cards:
            obs[idx] = hand_counts.get(card_name, 0) / 10.0
            idx += 1

        # Deck and discard sizes
        obs[idx] = len(player.deck) / 30.0
        idx += 1
        obs[idx] = len(player.discard) / 30.0
        idx += 1

        # Supply counts
        for card_name in self.all_cards:
            count = game_state.supply.get(card_name, 0)
            obs[idx] = count / 12.0  # Most piles start at 10-12
            idx += 1

        # Opponent info
        obs[idx] = len(opponent.hand) / 10.0
        idx += 1
        obs[idx] = (len(opponent.deck) + len(opponent.discard)) / 30.0
        idx += 1

        return obs

    def _count_cards(self, cards: list) -> dict[str, int]:
        """Count cards by name."""
        counts: dict[str, int] = {}
        for card in cards:
            name = card.name
            counts[name] = counts.get(name, 0) + 1
        return counts
