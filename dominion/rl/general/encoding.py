"""Stable card vocabulary, reproducible kingdom splits, and player observations."""

from collections import Counter
import hashlib
from itertools import combinations
from pathlib import Path
import random

import numpy as np

from dominion.cards.registry import get_card
from dominion.rl.action_encoder import BASE_CARDS

# All optional decisions in this pool are covered by action/treasure/buy/trash.
# Moat is always revealed: in this pool blocking Witch has no downside.
CARD_POOL = (
    "Adventurer", "Chapel", "Council Room", "Farm", "Festival", "Gardens", "Great Hall",
    "Laboratory", "Market", "Merchant", "Moat", "Smithy", "Village",
    "Witch", "Woodcutter",
)
VOCABULARY = tuple(BASE_CARDS) + CARD_POOL
DECISIONS = ("action", "treasure", "buy", "trash")
SCHEMA_VERSION = 1


def source_fingerprint():
    """Identify the simulator and agent sources used for a run."""
    root = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def kingdom_splits(seed=1729, train_count=64, validation_count=8, test_count=12):
    counts = (train_count, validation_count, test_count)
    if any(n < 1 for n in counts):
        raise ValueError("Every split must contain at least one kingdom")
    boards = list(combinations(CARD_POOL, 10))
    if sum(counts) > len(boards):
        raise ValueError("Requested more distinct kingdoms than the pool provides")
    random.Random(seed).shuffle(boards)
    a, b = train_count, train_count + validation_count
    return {"train": [list(k) for k in boards[:a]],
            "validation": [list(k) for k in boards[a:b]],
            "test": [list(k) for k in boards[b:b + test_count]]}


def validate_kingdom(kingdom):
    if len(kingdom) != 10 or len(set(kingdom)) != 10 or not set(kingdom) <= set(CARD_POOL):
        raise ValueError("Expected ten distinct cards from the supported general-agent pool")


def validate_splits(splits):
    if set(splits) != {"train", "validation", "test"}:
        raise ValueError("Expected train, validation, and test kingdom splits")
    seen = set()
    for boards in splits.values():
        if not boards:
            raise ValueError("Kingdom splits must be nonempty")
        for board in boards:
            validate_kingdom(board)
            key = tuple(sorted(board))
            if key in seen:
                raise ValueError("Kingdom splits overlap or contain duplicates")
            seen.add(key)


class GeneralEncoder:
    """No opponent hand identities and no player's draw order are observed.

    Own deck composition is legitimate remembered information for this pool:
    starting cards, gains, and trashing are known. We aggregate the physical
    zones directly; their ordering never enters the observation. Opponent
    information is restricted to zone sizes and public turn counts.
    """

    card_features = 19
    global_features = 17
    observation_size = len(VOCABULARY) * card_features + global_features

    def __init__(self):
        cards = [get_card(n) for n in VOCABULARY]
        self.static = np.asarray([
            [c.cost.coins / 8, c.stats.cards / 4, c.stats.actions / 2,
             c.stats.coins / 3, c.stats.buys / 2, c.stats.vp / 6,
             c.is_action, c.is_treasure, c.is_victory, c.name == "Curse",
             c.is_attack, c.is_reaction] for c in cards
        ], dtype=np.float32)

    def encode_decision(self, state, player_index, decision_type):
        me, other = state.players[player_index], state.players[1 - player_index]
        # Only these four zones exist for cards in the supported pool.
        hand = Counter(c.name for c in me.hand)
        deck = Counter(c.name for c in me.deck)
        discard = Counter(c.name for c in me.discard)
        in_play = Counter(c.name for c in me.in_play)
        owned = hand + deck + discard + in_play
        tokens = np.empty((len(VOCABULARY), self.card_features), dtype=np.float32)
        tokens[:, :12] = self.static
        for i, name in enumerate(VOCABULARY):
            tokens[i, 12:] = (name in state.supply, state.supply.get(name, 0) / 12,
                              hand[name] / 5, owned[name] / 20,
                              discard[name] / 20, in_play[name] / 5, deck[name] / 20)
        globals_ = [me.actions / 4, me.buys / 4, me.coins / 8,
                    state.turn_number / 30, sum(owned.values()) / 30,
                    len(me.hand) / 10, me.get_victory_points() / 50,
                    sum(n == 0 for n in state.supply.values()) / 3,
                    player_index, len(other.hand) / 10, len(other.deck) / 30,
                    len(other.discard) / 30, (me.turns_taken - other.turns_taken) / 2]
        globals_ += [float(decision_type == d) for d in DECISIONS]
        return np.concatenate((tokens.ravel(), np.asarray(globals_, dtype=np.float32)))
