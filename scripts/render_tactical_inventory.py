"""Render one evidence inventory covering every canonical registered card.

Reviewed entries are deliberately scoped by decision. A card's other effects
and every absent entry remain unreviewed, even if unrelated tests exist.
"""

from collections import Counter
from dataclasses import dataclass
import inspect
from pathlib import Path

from dominion.cards.registry import CARD_TYPES
from dominion.reporting.strategy_pages import card_expansion

OUTPUT = Path("docs/card-tactical-inventory.md")


@dataclass(frozen=True)
class Audit:
    decision: str
    rules: str
    wiring: str
    tactical: str
    hooks: tuple[str, ...]
    evidence: tuple[str, ...]
    followups: tuple[int, ...] = ()
    adapter: str = "dominion/ai/genetic_ai.py"


def reviewed_decisions():
    audits = {}

    def add(names, decision, hooks, tests, *, rules="Targeted regression audit; other interactions unreviewed",
            wiring="Connected/tested", tactical="Unreviewed", evidence=(), followups=(),
            adapter="dominion/ai/genetic_ai.py"):
        for name in names:
            audits[name] = Audit(decision, rules, wiring, tactical, tuple(hooks),
                                 tuple(tests) + tuple(evidence), tuple(followups), adapter)

    add(("Overlord", "Captain", "Band of Misfits"), "Supply Action target",
        ("choose_overlord_target", "choose_captain_target", "choose_band_of_misfits_target"),
        ("tests/test_shared_card_tactics.py",), rules="Targeted menus; open proxy/indirect-play/scheduling defects",
        tactical="Evaluated: fixed non-Duration panel only",
        evidence=("scripts/data/supply_action_evaluation.json", "reports/strategies/supply-action-selection-evaluation.html"),
        followups=(390, 395, 396, 397, 405))
    for name in ("Overlord", "Captain", "Band of Misfits"):
        a = audits[name]
        hook = "choose_" + name.lower().replace(" ", "_") + "_target"
        audits[name] = Audit(a.decision, a.rules, a.wiring, a.tactical, (hook,), a.evidence, a.followups)

    add(("Workshop", "Remodel", "Anvil", "Quartermaster"), "Free gain / sacrifice / storage",
        ("choose_free_gain",), ("tests/test_free_gain_tactics.py", "tests/test_free_gain_evaluation.py"),
        tactical="Evaluated: mixed/regressing fixed panels",
        evidence=("scripts/data/free_gain_tactics_evaluation-2026-10-08-anvil-adapter.json",
                  "reports/strategies/free-gains-and-quartermaster-policy-evaluation.html"), followups=(391,))
    specific = {"Remodel": ("choose_remodel_option",),
                "Anvil": ("choose_anvil_option", "choose_anvil_gain", "choose_anvil_treasure_to_discard"),
                "Quartermaster": ("choose_quartermaster_option", "choose_quartermaster_gain", "quartermaster_take_all")}
    for name, hooks in specific.items():
        a = audits[name]
        audits[name] = Audit(a.decision, a.rules, a.wiring, a.tactical, a.hooks + hooks, a.evidence, a.followups)

    add(("Chapel", "Junk Dealer"), "Optional bounded / mandatory trash",
        ("choose_card_to_trash",), ("tests/test_set_aside_tactics.py",),
        tactical="Needs context: scenario coverage; strength not isolated", followups=(392,))
    a = audits["Junk Dealer"]
    audits["Junk Dealer"] = Audit(a.decision, a.rules, a.wiring, a.tactical,
                                ("choose_card_to_trash_with_junk_dealer",), a.evidence, a.followups)
    for name, hook in (("Gear", "choose_gear_set_aside"), ("Haven", "choose_card_to_set_aside_for_haven")):
        add((name,), "Next-turn set-aside", (hook,), ("tests/test_set_aside_tactics.py",),
            tactical="Evaluated: fixed kingdom; engine score regressions",
            evidence=("reports/strategies/trashing-discard-and-next-turn-card-decisions.html",), followups=(392, 398))
    add(("Courier",), "Optional Action/Treasure play from discard", ("choose_courier_target",),
        ("tests/test_courier.py",), followups=(348,))
    for name, hook in (("Barge", "should_resolve_barge_now"), ("Sleigh", "choose_sleigh_reaction")):
        add((name,), "Timing / gain destination", (hook,), ("tests/test_menagerie_cards.py",),
            wiring="Needs forwarding", rules="Existing card tests; strategy path absent",
            tactical="Needs context", followups=(393, 407) if name == "Barge" else (393, 409, 410))
    add(("Torturer",), "Attack mode and discards", ("choose_torturer_attack", "choose_cards_to_discard"),
        ("tests/test_groundskeeper_margrave.py",),
        rules="Forwarding tests; full response/menu audit remains with #393", tactical="Needs context", followups=(393, 406, 408))

    for name, hooks in (
        ("Watchtower", ("choose_watchtower_reaction",)),
        ("Clerk", ("choose_card_to_topdeck_for_clerk", "should_play_clerk_reaction")),
        ("Investment", ("choose_investment_mode", "choose_card_to_trash")),
        ("Bounty Hunter", ("choose_card_to_exile_for_bounty_hunter",)),
    ):
        add((name,), "Gain reaction" if name == "Watchtower" else "Attack response / start-turn reaction" if name == "Clerk"
            else "Mandatory hand trash / self-trash mode" if name == "Investment" else "Exile target / first-name bonus",
            hooks, ("tests/test_card_tactics_evaluation.py", "tests/test_genetic_ai_hooks.py",
                    "tests/test_menagerie_cards.py" if name == "Bounty Hunter" else "tests/test_prosperity_cards.py"),
            tactical="Evaluated: fixed money panel; Clerk reaction timing unchanged" if name == "Clerk"
                else "Evaluated: fixed money panel; no universal improvement",
            evidence=("scripts/data/card_tactics_screen.json", "scripts/data/card_tactics_validation.json",
                      "reports/strategies/card-reactions-investment-and-exile-evaluation.html"),
            followups=(394, 411, 413) if name == "Investment" else (394, 413))

    extra = (
        ("Knights", "Shared victim trash; each member's extras unreviewed", ("choose_card_to_trash_for_knight_attack",)),
        ("Rogue", "Victim trash; trash-pile gain policy unreviewed", ("choose_card_to_trash_for_rogue_attack",)),
        ("Stables", "Optional Treasure discard", ("choose_treasure_to_discard_for_stables",)),
        ("Spice Merchant", "Optional Treasure trash and mode", ("choose_treasure_to_trash_for_spice_merchant", "choose_spice_merchant_mode")),
        ("Armory", "Mandatory deck gain", ("choose_armory_gain",)),
        ("Artificer", "Discard budget / deck gain", ("choose_artificer_gain", "choose_cards_to_discard")),
        ("Scheme", "Clean-up topdeck", ("choose_card_to_topdeck_for_scheme",)),
    )
    for name, decision, hooks in extra:
        add((name,), decision, hooks, ("tests/test_kolkata_board_cards.py",), followups=(394,))
    # The ten member entries are scoped to the shared victim decision only.
    from dominion.cards.dark_ages.knights import KNIGHT_NAMES
    for name in KNIGHT_NAMES:
        audits[name] = audits["Knights"]

    add(("Ironworks",), "Mandatory free gain via purchase selector", ("choose_buy",),
        ("tests/test_suzhou_board_rules.py",), wiring="Needs context: connected purchase priorities",
        tactical="Needs context: no independent free-gain parameters", followups=(412,))
    add(("Engineer",), "Optional self-trash and free gains via purchase selector",
        ("should_trash_engineer_for_extra_gains", "choose_buy"), ("tests/test_recruiter_kitsune_rules.py",),
        wiring="Needs context: self-trash connected; gains reuse purchases",
        tactical="Needs context: gain destination / ownership", followups=(412,), adapter="dominion/ai/base_ai.py")
    add(("Counterfeit",), "Optional Treasure replay/trash", ("should_replay_treasure_with_counterfeit",),
        ("tests/test_recruiter_kitsune_rules.py",), adapter="dominion/ai/base_ai.py")
    add(("Moneylender",), "Optional Copper trash", ("should_trash_copper_for_moneylender",),
        ("tests/test_groundskeeper_margrave.py",))
    add(("Minion",), "Money vs redraw", ("choose_minion_mode",), ("tests/test_three_unused_kingdoms.py",))
    add(("Courtier",), "Reveal and bonus combination", ("choose_courtier_reveal", "choose_courtier_options"),
        ("tests/test_three_unused_kingdoms.py",), wiring="Needs forwarding for reveal; bonuses connected/tested", followups=(344,))
    return audits


def inventory():
    audits = reviewed_decisions()
    unknown = audits.keys() - CARD_TYPES.keys()
    if unknown:
        raise ValueError(f"Unregistered audited cards: {sorted(unknown)}")
    return [(name, card_expansion(name), audits.get(name))
            for name in sorted(CARD_TYPES, key=lambda n: (card_expansion(n), n))]


def link(path):
    return f"[`{path}`](../{path})"


def render():
    rows = inventory()
    counts = Counter(expansion for _, expansion, _ in rows)
    reviewed = Counter(expansion for _, expansion, audit in rows if audit)
    lines = ["# Card decision evidence inventory", "",
        "Generated from `scripts/render_tactical_inventory.py` and the canonical card registry.",
        "Run `PYTHONPATH=. python scripts/render_tactical_inventory.py` after adding cards or evidence.", "",
        "This is the coverage source for [the shared-decision plan](card-tactical-defaults.md) and "
        "[parent #344](https://github.com/jss367/py-overlord/issues/344). Rules audits, engine wiring, "
        "and tactical evaluation are independent columns. Evaluated means measured on the declared panel, "
        "including losses; it does not certify strong play. Connected/tested does not imply evaluated. "
        "Needs forwarding and needs context remain open implementation work. Unreviewed means no claim "
        "in this audit, including for fixed-effect cards and their action order. Member cards and non-Supply "
        "cards are listed separately; counts are registered names, not kingdom piles.", "",
        "Merged decision work: [#404](https://github.com/jss367/py-overlord/pull/404) (supply targets), "
        "[#403](https://github.com/jss367/py-overlord/pull/403) (free gains), "
        "[#402](https://github.com/jss367/py-overlord/pull/402) (trash/discard/storage), "
        "[#348](https://github.com/jss367/py-overlord/pull/348) (Courier). "
        "Source inspection is limited to the named hooks and linked tests.", "",
        "## Coverage by expansion", "", "| Expansion | Registered names | Scoped reviewed entries | Unreviewed entries |",
        "| --- | ---: | ---: | ---: |"]
    for expansion in sorted(counts):
        lines.append(f"| {expansion} | {counts[expansion]} | {reviewed[expansion]} | {counts[expansion] - reviewed[expansion]} |")
    lines += ["", f"Total: {len(rows)} registered names; {sum(reviewed.values())} scoped entries; "
              f"{len(rows) - sum(reviewed.values())} unreviewed.", "",
              "Priority: finish active kingdoms and #393 timing/response coverage, then review Base, "
              "Prosperity, Menagerie and the remaining expansions. Ironworks and Engineer expose additional "
              "free-gain context gaps; their hooks are not duplicated here.", "",
              "## Scoped evidence", "",
              "| Card | Expansion | Decision | Rules audit | Engine → AI wiring | Tactical evaluation | Evidence / follow-ups |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for name, expansion, audit in rows:
        if not audit:
            continue
        hooks = ", ".join(f"`{hook}`" for hook in audit.hooks)
        evidence = "; ".join(link(p) for p in audit.evidence)
        engine = Path(inspect.getfile(CARD_TYPES[name])).resolve().relative_to(Path.cwd())
        evidence = link(str(engine)) + "; " + evidence
        issues = ", ".join(f"[#{n}](https://github.com/jss367/py-overlord/issues/{n})" for n in audit.followups)
        lines.append(f"| {name} | {expansion} | {audit.decision} | {audit.rules} | "
                     f"{audit.wiring}: {link(audit.adapter)} → {hooks} | {audit.tactical} | {evidence}; {issues} |")
    lines += ["", "## Explicitly unreviewed cards", "",
              "Each row has unreviewed rules, wiring and tactical quality in this inventory. "
              "A source link identifies the implementation to audit, not evidence of correctness.", "",
              "| Card | Expansion | Decision | Rules | Wiring | Tactics | Source |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    root = Path.cwd()
    for name, expansion, audit in rows:
        if audit:
            continue
        source = Path(inspect.getfile(CARD_TYPES[name])).resolve().relative_to(root)
        lines.append(f"| {name} | {expansion} | Unreviewed | Unreviewed | Unreviewed | Unreviewed | {link(str(source))} |")
    lines += ["", "## Optimizer coverage is separate", "",
        "Bounty Hunter's `bounty_hunter_exile_priority` already round-trips through "
        "`dominion/simulation/structured_genome.py`, mutates in the genetic trainer, and has "
        "tests in `tests/test_structured_genome.py`. This exposes priority rules, not the complete "
        "contextual bonus policy in the benchmark. Free-gain preferences also round-trip, but arbitrary "
        "Python Watchtower, Clerk, Investment, supply-target, timing and storage overrides are not "
        "automatically searchable genes. A callable hook and a parameterized policy are separate claims.", "",
        "Baseline-change rule: freeze the candidate and purchases before fresh seat-balanced validation, "
        "record decision firings and raw seed outcomes, and reevaluate every affected registered strategy "
        "on its own board before changing production defaults. This measurement changes no defaults; "
        "existing supply, free-gain and storage studies contain their own strategy reevaluations. "
        "Historical standings remain historical evidence.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    OUTPUT.write_text(render())
