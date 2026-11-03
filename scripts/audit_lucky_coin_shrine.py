"""Replay Shrine games and retain concrete missed-Copper opportunities."""

import argparse
from collections import Counter
import json
from pathlib import Path

from dominion.game.game_state import GameState
from generated_strategies.lucky_coin_cleanup import LuckyCoinCleanup
from scripts.search_lucky_coin_cleanup import CHAMPION
from scripts.search_lucky_coin_ruins import setup


def snapshot(s, p):
    return dict(
        turn=p.turns_taken,
        phase=s.phase,
        coins=p.coins,
        buys=p.buys,
        hand=dict(Counter(c.name for c in p.hand)),
        shrine_charges=sum(getattr(c, "shrine_charges", 0) for c in p.duration),
        highwayman_block_pending=bool(
            p.highwayman_attacks and not p.highwayman_blocked_this_turn
        ),
    )


def decision_wrapper(method):
    original = getattr(LuckyCoinCleanup, method)

    def traced(self, state, player, *args):
        result = original(self, state, player, *args)
        if (
            getattr(state, "audit_live_id", None) == id(state)
            and player is state.audit_player
        ):
            event = snapshot(state, player)
            event["decision"] = method
            event["choice"] = getattr(result, "name", getattr(result, "kind", None))
            if method == "choose_gain_effect":
                event["gained_card"] = args[0].name
                event["options"] = [e.kind for e in args[1]]
            state.audit_events.append(event)
        return result

    return traced


class TracedCleanup(LuckyCoinCleanup):
    pass


for _method in [
    "choose_action",
    "choose_treasure",
    "choose_gain",
    "choose_trash",
    "choose_gain_effect",
]:
    setattr(TracedCleanup, _method, decision_wrapper(_method))


class AuditState(GameState):
    def live(self, player=None):
        return getattr(self, "audit_live_id", None) == id(self) and (
            player is None or player is self.audit_player
        )

    def handle_treasure_phase(self):
        if self.live(self.current_player):
            self.audit_frame = dict(
                start=snapshot(self, self.current_player),
                events_start=len(self.audit_events),
                copper_income_plays=0,
                purchases=[],
            )
            self.audit_frames.append(self.audit_frame)
        super().handle_treasure_phase()
        if self.live(self.current_player):
            self.audit_frame["after_treasures"] = snapshot(self, self.current_player)

    def play_treasure_indirectly(self, player, card):
        before = player.coins
        result = super().play_treasure_indirectly(player, card)
        if (
            self.live(player)
            and self.audit_frame is not None
            and card.name == "Copper"
            and player.coins - before == 1
        ):
            self.audit_frame["copper_income_plays"] += 1
        return result

    def _commit_buy(self, player, card):
        if self.live(player) and self.audit_frame is not None:
            self.audit_frame["purchases"].append(
                dict(
                    name=card.name,
                    cost=self.get_card_cost(player, card),
                    coins=player.coins,
                )
            )
        return super()._commit_buy(player, card)

    def handle_buy_phase(self):
        super().handle_buy_phase()
        if self.live(self.current_player):
            self.audit_frame["end"] = snapshot(self, self.current_player)
            self.audit_frame["events"] = self.audit_events[
                self.audit_frame["events_start"] :
            ]


def audit_game(spec, seed, swap=False):
    s = setup(spec, CHAMPION, seed, swap, state_class=AuditState)
    p = s.players[int(swap)]
    p.ai.strategy.__class__ = TracedCleanup
    s.audit_live_id = id(s)
    s.audit_player = p
    s.audit_events = []
    s.audit_frames = []
    s.audit_frame = None
    while not s.is_game_over() and s.turn_number < 160:
        s.play_turn()
    misses = []
    for f in s.audit_frames:
        # Conservative case: a Copper produced $1; Shrine later declined an
        # empty trash slot in the Buy phase; enough unspent cash remained to
        # keep every actual purchase after withholding that Copper's $1.
        empty = [
            e
            for e in f["events"]
            if e["decision"] == "choose_trash"
            and e["choice"] is None
            and e["phase"] == "buy"
            and not e["hand"].get("Copper", 0)
        ]
        if (
            f["start"]["shrine_charges"] > 0
            and f["copper_income_plays"]
            and f["end"]["coins"] >= 1
            and all(b["coins"] - 1 >= b["cost"] for b in f["purchases"])
            and empty
        ):
            misses.append(
                dict(
                    turn=f["start"]["turn"],
                    treasure_start=f["start"],
                    after_treasures=f["after_treasures"],
                    purchases=f["purchases"],
                    declined_trash=empty[0],
                    unspent_coins=f["end"]["coins"],
                    events=[
                        e for e in s.audit_events if e["turn"] == f["start"]["turn"]
                    ],
                )
            )
    held_turns = [
        dict(
            turn=f["start"]["turn"],
            treasure_start=f["start"],
            after_treasures=f["after_treasures"],
            purchases=f["purchases"],
            events=[e for e in s.audit_events if e["turn"] == f["start"]["turn"]],
        )
        for f in s.audit_frames
        if f["after_treasures"]["hand"].get("Copper", 0)
    ]
    return dict(
        seed=seed,
        held_turns=held_turns,
        swap=swap,
        missed_turns=misses,
        turns=len(s.audit_frames),
        buy_phase_shrine_declines=sum(
            e["decision"] == "choose_trash"
            and e["choice"] is None
            and e["phase"] == "buy"
            for e in s.audit_events
        ),
        copper_held_at_buy=sum(
            f["after_treasures"]["hand"].get("Copper", 0) > 0 for f in s.audit_frames
        ),
        result=[(x.get_victory_points(), x.turns_taken) for x in s.players],
        truncated=not s._normal_game_end_reached(),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--specs",
        type=Path,
        default=Path("scripts/data/lucky_coin_ruins/cleanup-validation-specs.json"),
    )
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--games", type=int, default=400)
    parser.add_argument("--seed", type=int, default=5000000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.games < 2 or args.games % 2:
        parser.error("--games must be positive and even")
    spec = json.loads(args.specs.read_text())[args.index]
    results = [
        audit_game(spec, args.seed + i // 2, bool(i % 2)) for i in range(args.games)
    ]
    misses = [
        dict(seed=r["seed"], swap=r["swap"], **m)
        for r in results
        for m in r["missed_turns"]
    ]
    out = dict(
        spec=spec,
        seed=args.seed,
        games=args.games,
        turns=sum(r["turns"] for r in results),
        games_with_misses=sum(bool(r["missed_turns"]) for r in results),
        missed_turns=len(misses),
        copper_held_at_buy=sum(r["copper_held_at_buy"] for r in results),
        truncated=sum(r["truncated"] for r in results),
        examples=misses[:5],
        held_examples=[
            dict(seed=r["seed"], swap=r["swap"], **turn)
            for r in results
            for turn in r["held_turns"]
        ][:5],
    )
    args.output.write_text(json.dumps(out, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in out.items()
                if k not in ("examples", "held_examples", "spec")
            },
            indent=2,
        )
    )
    for x in misses[:2]:
        print(json.dumps({k: v for k, v in x.items() if k != "events"}, indent=2))


if __name__ == "__main__":
    main()
