"""Shared card scorer, synchronous game adapter, and versioned checkpoints."""

from pathlib import Path
from types import SimpleNamespace

import torch
from torch import nn

from dominion.ai.base_ai import AI
from dominion.rl.action_encoder import ActionEncoder
from dominion.rl.networks import MLPPolicy
from dominion.rl.general.encoding import (
    CARD_POOL, VOCABULARY, SCHEMA_VERSION, GeneralEncoder, validate_kingdom, validate_splits,
)


class GeneralPolicy(MLPPolicy):
    """One shared scorer for card features plus a learned card identity.

    Pooling shares contextual information across supply/deck cards. There is
    one output per card and a separate pass output; legal menus mask both.
    """

    def __init__(self):
        nn.Module.__init__(self)
        self.identities = nn.Embedding(len(VOCABULARY), 8)
        self.card_encoder = nn.Sequential(
            nn.Linear(GeneralEncoder.card_features + 8, 64), nn.ReLU(),
            nn.Linear(64, 64), nn.ReLU())
        self.context = nn.Sequential(
            nn.Linear(128 + GeneralEncoder.global_features, 128), nn.ReLU())
        self.card_head = nn.Sequential(nn.Linear(192, 64), nn.ReLU(), nn.Linear(64, 1))
        self.pass_head = nn.Linear(128, 1)
        self.value_head = nn.Linear(128, 1)

    def forward(self, obs):
        n = len(VOCABULARY)
        tokens = obs[:, :n * GeneralEncoder.card_features].reshape(
            -1, n, GeneralEncoder.card_features)
        identities = self.identities.weight.unsqueeze(0).expand(obs.shape[0], -1, -1)
        cards = self.card_encoder(torch.cat((tokens, identities), dim=-1))
        context = self.context(torch.cat((cards.mean(1), cards.amax(1),
                                         obs[:, -GeneralEncoder.global_features:]), dim=-1))
        scores = self.card_head(torch.cat((cards, context.unsqueeze(1).expand(-1, n, -1)),
                                         dim=-1)).squeeze(-1)
        return torch.cat((scores, self.pass_head(context)), dim=-1), self.value_head(context)


class GeneralAI(AI):
    """Play a supported kingdom directly in GameState, without a Gym thread."""

    # Match RLAI: prohibit cloned decision probes and the engine's heuristic
    # losing-purchase filter. The network must learn endgame choices itself.
    decision_hooks_are_pure = False

    def __init__(self, policy, *, name="General Dominion agent", sample=False):
        self.policy = policy
        self.encoder = GeneralEncoder()
        self.actions = ActionEncoder(list(CARD_POOL))
        self.strategy = SimpleNamespace(name=name)
        self.sample = sample
        self._validated_state = None

    @property
    def name(self):
        return self.strategy.name

    def decide(self, state, choices, decision):
        if self._validated_state is not state:
            if len(state.players) != 2:
                raise ValueError("General agent currently supports two-player games only")
            validate_kingdom(state.original_kingdom_pile_names)
            if (state.events or state.projects or state.ways or state.landmarks or state.allies
                    or state.prophecy or state.trait_piles or state.setup_card_cost_reduction):
                raise ValueError("General agent does not yet support landscapes or modified setup rules")
            self._validated_state = state
        seat = next(i for i, p in enumerate(state.players) if p.ai is self)
        obs = self.encoder.encode_decision(state, seat, decision)
        mask = torch.from_numpy(self.actions.get_action_mask(choices)).unsqueeze(0)
        with torch.inference_mode():
            logits, _ = self.policy(torch.from_numpy(obs).unsqueeze(0))
            logits = logits.masked_fill(~mask, float("-inf"))
            index = (torch.distributions.Categorical(logits=logits).sample().item()
                     if self.sample else logits.argmax(-1).item())
        if index == self.actions.pass_action_index:
            return None
        name = self.actions.all_cards[index]
        return next(c for c in choices if c is not None and c.name == name)

    def choose_action(self, state, choices):
        return self.decide(state, choices, "action")

    def choose_treasure(self, state, choices):
        return self.decide(state, choices, "treasure")

    def choose_buy(self, state, choices):
        return self.decide(state, choices, "buy")

    def choose_card_to_trash(self, state, choices):
        return self.decide(state, choices, "trash")


def save_checkpoint(path, policy, metadata, optimizer=None):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": SCHEMA_VERSION, "vocabulary": list(VOCABULARY),
               "policy_state_dict": policy.state_dict(), "metadata": metadata}
    if optimizer is not None:
        payload["optimizer_state_dict"] = optimizer.state_dict()
    temporary = Path(str(path) + ".tmp")
    torch.save(payload, temporary)
    temporary.replace(path)


def load_checkpoint(path):
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("vocabulary") != list(VOCABULARY):
        raise ValueError("Checkpoint vocabulary or observation schema is incompatible")
    validate_splits(payload["metadata"]["splits"])
    policy = GeneralPolicy()
    policy.load_state_dict(payload["policy_state_dict"])
    policy.eval()
    return policy, payload["metadata"]
