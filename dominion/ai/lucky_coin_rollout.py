"""Information-limited, phase-replayed rollout planning for the Lucky Coin board.

The same planner wraps either continuation policy. It changes legal actions,
Treasures, purchases, gains, trashes and Spice Merchant decisions. Future play
uses those continuation policies, so this is bounded policy improvement rather
than an optimal-game solver.
"""

from collections import Counter
import copy
from dataclasses import dataclass
import hashlib
import json
from math import comb
import random

from dominion.ai.genetic_ai import GeneticAI


class ReplayMismatch(RuntimeError):
    pass


def label(choice):
    if choice is None:
        return "pass"
    if hasattr(choice, "kind"):
        return f"effect:{choice.kind}:{getattr(choice.source, 'name', '')}"
    if hasattr(choice, "name"):
        return choice.name
    return str(choice)


def menu(choices):
    return dict((label(c), c) for c in choices)


def public_observation(state, player, known_top=()):
    """A seed key containing no unknown card order or opponent hand contents."""
    return dict(
        player=state.players.index(player),
        phase=state.phase,
        turn=player.turns_taken,
        actions=player.actions,
        coins=player.coins,
        buys=player.buys,
        debt=player.debt,
        hand=sorted(Counter(c.name for c in player.hand).items()),
        deck_counts=sorted(Counter(c.name for c in player.deck).items()),
        known_top=list(known_top),
        supply=sorted(state.supply.items()),
        players=[
            dict(
                discard=sorted(Counter(c.name for c in p.discard).items()),
                play=sorted(Counter(c.name for c in p.in_play).items()),
                hand_size=len(p.hand),
                deck_size=len(p.deck),
                owned=sorted(Counter(c.name for c in p.all_cards()).items()),
                turns=p.turns_taken,
                debt=p.debt,
            )
            for p in state.players
        ],
        sun=state.sun_tokens,
    )


def determinize(state, player_index, seed, known_top=()):
    """Sample hidden zones canonically, preserving observed own top cards."""
    rng = random.Random(seed)
    for index, player in enumerate(state.players):
        if index == player_index:
            top = player.deck[-len(known_top) :] if known_top else []
            if known_top and [c.name for c in reversed(top)] != list(known_top):
                raise ReplayMismatch("Known top cards differ during replay")
            hidden = sorted(
                player.deck[: -len(top)] if top else player.deck, key=lambda c: c.name
            )
            rng.shuffle(hidden)
            player.deck = hidden + top
        else:
            count = len(player.hand)
            hidden = sorted(player.hand + player.deck, key=lambda c: c.name)
            rng.shuffle(hidden)
            player.hand, player.deck = hidden[:count], hidden[count:]
    if getattr(state, "boons_deck", None):
        state.boons_deck = sorted(state.boons_deck)
        rng.shuffle(state.boons_deck)
    random.seed(seed)


@dataclass
class Decision:
    checkpoint: object
    rng: object
    prefix: list
    kind: str
    player: int
    options: list
    baseline: str
    observation: dict
    known_top: list
    identifier: dict


def detached_copy(state):
    clone = copy.deepcopy(state)
    for p in clone.players:
        # GameState copies share AI objects; replace them before any rollout.
        p.ai = GeneticAI(copy.deepcopy(p.ai.strategy))
    return clone


class RolloutAI(GeneticAI):
    def __init__(self, strategy, controller):
        super().__init__(strategy)
        self.controller = controller

    @property
    def allow_legacy_change_pass(self):
        """Only explicitly versioned research replays may use the old rule bug."""
        return self.controller.allow_legacy_change_pass

    def choose_action(self, s, choices):
        return self.controller.choose(
            "action",
            s,
            s.current_player,
            choices,
            lambda: super(RolloutAI, self).choose_action(s, choices),
        )

    def choose_treasure(self, s, choices):
        return self.controller.choose(
            "treasure",
            s,
            s.current_player,
            choices,
            lambda: super(RolloutAI, self).choose_treasure(s, choices),
        )

    def choose_buy(self, s, choices):
        kind = "buy" if s.phase == "buy" else "gain"
        return self.controller.choose(
            kind,
            s,
            s.current_player,
            choices,
            lambda: super(RolloutAI, self).choose_buy(s, choices),
        )

    def choose_card_to_trash(self, s, choices):
        return self.controller.choose(
            "trash",
            s,
            s.current_player,
            choices,
            lambda: super(RolloutAI, self).choose_card_to_trash(s, choices),
        )

    def choose_free_gain(self, s, p, choices, context):
        offered = list(choices) + ([None] if not context.mandatory else [])
        return self.controller.choose(
            "free_gain",
            s,
            p,
            offered,
            lambda: super(RolloutAI, self).choose_free_gain(s, p, choices, context),
        )

    def choose_kind_emperor_gain(self, s, p, choices):
        return self.controller.choose(
            "emperor",
            s,
            p,
            choices,
            lambda: super(RolloutAI, self).choose_kind_emperor_gain(s, p, choices),
        )

    def choose_gain_effect(self, s, p, card, choices):
        return self.controller.choose(
            "effect",
            s,
            p,
            choices,
            lambda: super(RolloutAI, self).choose_gain_effect(s, p, card, choices),
        )

    def choose_treasure_to_trash_for_spice_merchant(self, s, p, choices):
        return self.controller.choose(
            "spice_trash",
            s,
            p,
            list(choices) + [None],
            lambda: super(RolloutAI, self).choose_treasure_to_trash_for_spice_merchant(
                s, p, choices
            ),
        )

    def choose_spice_merchant_mode(self, s, p):
        return self.controller.choose(
            "spice_mode",
            s,
            p,
            ["cards", "coins"],
            lambda: super(RolloutAI, self).choose_spice_merchant_mode(s, p),
        )

    def order_cards_for_topdeck(self, s, p, cards):
        result = super().order_cards_for_topdeck(s, p, cards)
        self.controller.observe_top(s, p, result)
        return result

    def choose_card_to_topdeck_from_discard(self, s, p, choices):
        result = super().choose_card_to_topdeck_from_discard(s, p, choices)
        if result is not None:
            self.controller.observe_top(s, p, [result])
        return result


class RolloutController:
    """Allocate bounded searches without letting early choices consume every slot.

    ``legacy`` splits decisions_per_turn between strategic and tactical choices.
    ``cleanup`` uses separate per-player-turn quotas: one purchase, one gain,
    two trash choices, one armed-Shrine Treasure choice, and one Spice mode.
    Its named quotas replace decisions_per_turn. Adaptive discovery replaces
    fixed refinement when configured; independent verification remains separate.
    """

    def __init__(
        self,
        *,
        samples=2,
        refine=4,
        verify=16,
        decisions_per_turn=2,
        enabled=(True, True),
        observer=None,
        search_kinds=None,
        allow_legacy_change_pass=False,
        schedule="legacy",
        adaptive_refine=None,
    ):
        if samples < 1 or refine < 0 or verify < 0 or decisions_per_turn < 2:
            raise ValueError(
                "Require samples >= 1, refine/verify >= 0 and decision budget >= 2"
            )
        if schedule not in ("legacy", "cleanup") or (
            adaptive_refine is not None and adaptive_refine < 0
        ):
            raise ValueError("Invalid schedule or adaptive refinement budget")
        self.schedule, self.adaptive_refine = schedule, adaptive_refine
        self.samples, self.refine, self.verify = samples, refine, verify
        self.decisions_per_turn = decisions_per_turn
        self.enabled = enabled
        self.observer = observer
        self.allow_legacy_change_pass = allow_legacy_change_pass
        self.search_kinds = None if search_kinds is None else frozenset(search_kinds)
        self.live = None
        self.checkpoint = None
        self.prefix = []
        self.replay = None
        self.knowledge = {}
        self.used = {}
        self.records = []
        self.rollouts = 0

    def install(self, state):
        for p in state.players:
            p.ai = RolloutAI(p.ai.strategy, self)

    def begin(self, state, identifier=None):
        self.live = state
        self.checkpoint = detached_copy(state)
        self.phase_rng = random.getstate()
        self.prefix = []
        self.identifier = dict(
            identifier or {},
            phase=state.phase,
            turn=state.current_player.turns_taken,
            seat=state.current_player_index,
        )

    def observe_top(self, s, p, cards):
        if s is not self.live or self.replay is not None:
            return
        index = s.players.index(p)
        shuffle = getattr(p, "shuffle_count", 0)
        old = self.knowledge.get(index, (shuffle, []))
        seen = old[1] if old[0] == shuffle else []
        self.knowledge[index] = (shuffle, list(dict.fromkeys(seen + list(cards))))

    def known_top(self, s, p):
        entry = self.knowledge.get(s.players.index(p))
        if entry is None or entry[0] != getattr(p, "shuffle_count", 0):
            return []
        known = set(entry[1])
        result = []
        for c in reversed(p.deck):
            if c not in known:
                break
            result.append(c.name)
        return result

    def choose(self, kind, s, p, choices, baseline_fn):
        offered = menu(choices)
        index = s.players.index(p)
        if self.replay is not None and s is self.replay["state"]:
            replay = self.replay
            if replay["position"] < len(replay["decision"].prefix):
                entry = replay["decision"].prefix[replay["position"]]
                replay["position"] += 1
                if (kind, index, list(offered)) != (
                    entry["kind"],
                    entry["player"],
                    entry["options"],
                ):
                    raise ReplayMismatch("Decision prefix diverged")
                if entry["choice"] == "pass" and "pass" not in offered:
                    return None
                if entry["choice"] not in offered:
                    raise ReplayMismatch("Prior choice is unavailable")
                return offered[entry["choice"]]
            if not replay["hit"]:
                d = replay["decision"]
                if (kind, index, list(offered)) != (d.kind, d.player, d.options):
                    raise ReplayMismatch("Target decision diverged")
                if public_observation(s, p, d.known_top) != d.observation:
                    raise ReplayMismatch("Public observation differs at target")
                replay["hit"] = True
                determinize(s, index, replay["seed"], d.known_top)
                return offered[replay["choice"]]
            return baseline_fn()
        baseline = baseline_fn()
        if s is not self.live or self.replay is not None:
            return baseline
        base_label = label(baseline)
        if base_label not in offered:
            # Mandatory engine fallbacks are retained, not treated as legal passes.
            if baseline is None:
                self.prefix.append(
                    dict(kind=kind, player=index, options=list(offered), choice="pass")
                )
                return baseline
            raise ReplayMismatch(f"Baseline {base_label} absent from {kind} menu")
        known = self.known_top(s, p)
        d = Decision(
            self.checkpoint,
            self.phase_rng,
            list(self.prefix),
            kind,
            index,
            list(offered),
            base_label,
            public_observation(s, p, known),
            known,
            dict(self.identifier, decision=len(self.prefix)),
        )
        if self.observer is not None and len(offered) > 1:
            self.observer(d)
        chosen = base_label
        if self.schedule == "cleanup":
            category = {
                "buy": "purchase",
                "emperor": "gain",
                "free_gain": "gain",
                "gain": "gain",
                "trash": "shrine-trash",
                "spice_mode": "spice-mode",
                "treasure": "treasure-stop",
            }.get(kind)
            limit = 2 if kind == "trash" else 1
            # The existing heuristic handles ordinary Treasure sequencing.
            # Reserve rollout search for stop/play choices while Shrine is armed.
            if kind == "treasure" and not any(
                getattr(c, "shrine_armed", False) for c in p.duration
            ):
                category = None
        else:
            category = (
                "strategic"
                if kind in ("buy", "emperor", "free_gain", "gain")
                else "tactical"
            )
            limit = max(1, self.decisions_per_turn // 2)
        budget_key = (index, p.turns_taken, category)
        if (
            self.enabled[index]
            and category is not None
            and (self.search_kinds is None or kind in self.search_kinds)
            and len(offered) > 1
            and self.used.get(budget_key, 0) < limit
        ):
            self.used[budget_key] = self.used.get(budget_key, 0) + 1
            result = (
                self.evaluate(
                    d, self.samples, self.refine, adaptive=self.adaptive_refine
                )
                if self.adaptive_refine is not None
                else self.evaluate(d, self.samples, self.refine)
            )
            result["budget_group"] = category
            result["proposed_choice"] = result["choice"]
            if self.verify and result["choice"] != base_label:
                diffs = []
                for j in range(self.verify):
                    seed = self.sample_seed(d, j, salt=3)
                    a = self.outcome(d, base_label, seed)
                    b = self.outcome(d, result["choice"], seed)
                    diffs.append(b - a)
                positive = sum(x > 0 for x in diffs)
                nonzero = sum(x != 0 for x in diffs)
                pvalue = (
                    sum(comb(nonzero, j) for j in range(positive, nonzero + 1))
                    / 2**nonzero
                )
                result["verification"] = dict(
                    samples=self.verify,
                    mean_delta=sum(diffs) / len(diffs),
                    positive=positive,
                    nonzero=nonzero,
                    paired_sign_p=pvalue,
                )
                if pvalue > 0.05 or sum(diffs) <= 0:
                    result["choice"] = base_label
            elif not self.verify and result["paired_delta"] <= result["paired_se"]:
                # Reproduce the original low-budget exploratory configuration.
                result["choice"] = base_label
            chosen = result["choice"]
            self.records.append(result)
        self.prefix.append(
            dict(kind=kind, player=index, options=list(offered), choice=chosen)
        )
        return offered[chosen]

    def outcome(self, decision, choice, seed):
        saved_rng = random.getstate()
        previous = self.replay
        try:
            s = detached_copy(decision.checkpoint)
            self.install(s)
            self.replay = dict(
                state=s,
                decision=decision,
                position=0,
                hit=False,
                choice=choice,
                seed=seed,
            )
            random.setstate(decision.rng)
            s.play_turn()
            if not self.replay["hit"]:
                raise ReplayMismatch("Phase completed before reaching target")
            while not s.is_game_over() and s.turn_number < 160:
                s.play_turn()
            if not s._normal_game_end_reached():
                raise ReplayMismatch("Continuation did not reach a normal game end")
            scores = [(p.get_victory_points(), -p.turns_taken) for p in s.players]
            mine = scores[decision.player]
            other = max(x for i, x in enumerate(scores) if i != decision.player)
            self.rollouts += 1
            return 1.0 if mine > other else 0.5 if mine == other else 0.0
        finally:
            self.replay = previous
            random.setstate(saved_rng)

    @staticmethod
    def sample_seed(decision, sample, salt=0):
        payload = json.dumps(
            [decision.kind, decision.options, decision.observation, salt],
            sort_keys=True,
        )
        base = int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")
        return (base + sample) % (2**63)

    def evaluate(self, d, samples, refine=0, *, salt=0, adaptive=None):
        # Store sample indices, not just outcomes: adaptive races may revisit
        # a candidate later, and paired comparisons must use matching worlds.
        values = {name: {} for name in d.options}

        def add(names, sample):
            seed = self.sample_seed(d, sample, salt)
            for name in names:
                values[name][sample] = self.outcome(d, name, seed)

        def rank(names):
            return sorted(
                names,
                key=lambda n: (
                    sum(values[n].values()) / len(values[n]),
                    n == d.baseline,
                ),
                reverse=True,
            )

        def paired(choice):
            shared = values[choice].keys() & values[d.baseline].keys()
            diffs = [values[choice][i] - values[d.baseline][i] for i in sorted(shared)]
            delta = sum(diffs) / len(diffs)
            se = (
                (sum((x - delta) ** 2 for x in diffs) / (len(diffs) - 1) / len(diffs))
                ** 0.5
                if len(diffs) > 1
                else 0
            )
            return delta, se, len(diffs)

        for sample in range(samples):
            add(d.options, sample)
        if adaptive is None:
            finalists = list(dict.fromkeys([d.baseline] + rank(d.options)[:2]))
            for sample in range(samples, samples + refine):
                add(finalists, sample)
            choice = rank(finalists if refine else d.options)[0]
        else:
            # Extra compute follows the current leaders, with the baseline
            # always retained. Discovery stopping never replaces independent
            # verification, whose sample salt is disjoint.
            choice = rank(d.options)[0]
            for start in range(samples, samples + adaptive, 4):
                leaders = list(dict.fromkeys([d.baseline] + rank(d.options)[:2]))
                for sample in range(start, min(start + 4, samples + adaptive)):
                    add(leaders, sample)
                choice = rank(leaders)[0]
                delta, se, _ = paired(choice)
                if choice != d.baseline and delta > se:
                    break
                if all(v == 1 for v in values[d.baseline].values()):
                    choice = d.baseline
                    break
        delta, se, paired_samples = paired(choice)
        return dict(
            paired_delta=delta,
            paired_se=se,
            paired_samples=paired_samples,
            identifier=d.identifier,
            kind=d.kind,
            player=d.player,
            observation=d.observation,
            baseline=d.baseline,
            choice=choice,
            discovery_rollouts=sum(len(v) for v in values.values()),
            estimates={
                name: dict(mean=sum(v.values()) / len(v), samples=len(v))
                for name, v in values.items()
            },
        )
