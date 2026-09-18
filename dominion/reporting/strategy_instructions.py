"""Explicit, parameter-aware instructions for custom decision policies.

Providers describe the implementation that owns a hook, not a strategy name.
An inherited hook keeps its description; an override needs its own description.
This is presentation metadata, independent of runnable strategy discovery.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionInstructions:
    introduction: str
    steps: tuple[str, ...]


def _stables_ninja_museum(strategy) -> dict[str, DecisionInstructions]:
    p = strategy.params

    def target(card, cap):
        noun = "copy" if cap == 1 else "copies"
        return f"{card} while you own fewer than {cap} {noun}."

    opening = []
    if p["stables"]:
        opening.append("Stables if available")
    opening += [f"your first {p['opening']}", f"your first {p['second']}"]
    opening_text = "On your first two turns, try " + ", then ".join(opening) + ". "
    if p["credit"]:
        opening_text += (
            f"If none is available, use Credit to gain {p['opening']} if you do not own it, "
            "otherwise Stables; take the saved target on Credit's gain choice. "
        )
    else:
        opening_text += "Do not buy Credit. "
    opening_text += "Otherwise take Silver if available, or pass. "
    late = "two or fewer Colonies or two or fewer Provinces remain"
    gains = [
        "Colony whenever available.",
        f"Province when {p['province_at']} or fewer Colonies remain, or from your turn {p['green_turn']}.",
        f"Duchy when {late}.",
    ]
    if p["platinums"] > 0:
        gains.append(target("Platinum", p["platinums"]))
    for card, key in (("Ninja", "ninjas"), ("Catapult", "catapults"), ("Watchtower", "watchtowers")):
        if p[key] > 0:
            gains.append(f"Your first {card}.")
    if p["money"] and p["golds"] > 0:
        gains.append(target("Gold", p["golds"]))
    if p["stables"] > 0:
        gains.append(target("Stables", p["stables"]))
    if p["villages"] > 0:
        gains.append(
            f"Harbor Village while you own fewer than {p['villages']} and fewer than "
            "your combined Ninja, Catapult, Silk Merchant and Watchtower count minus one."
        )
    for card, key in (
        ("Silk Merchant", "silks"), ("Conclave", "conclaves"), ("Innkeeper", "innkeepers"),
        ("Ninja", "ninjas"), ("Catapult", "catapults"), ("Figurine", "figurines"),
        ("Gold", "golds"), ("Pendant", "pendants"), ("Silver", "silvers"),
    ):
        if key in {"ninjas", "catapults"} and p[key] <= 1:
            continue  # The first-copy instruction already covers these targets.
        if p[key] > 0:
            gains.append(target(card, p[key]))
    if p["museum"]:
        # Read the actual policy's kingdom order rather than maintaining a second list.
        kingdom = [rule.card_name for rule in strategy.action_priority]
        gains.append(
            f"For Museum, when {late}, or from your turn {p['green_turn']}, "
            "collect missing card names in this order: "
            + ", ".join([*kingdom, "Rocks", "Gold", "Silver", "Estate", "Copper", "Curse"])
            + ". Include kingdom cards skipped during the earlier buying steps."
        )
    gains.append(f"Estate when {late}. Otherwise pass.")

    actions = ["Harbor Village."]
    if p["ninja_first"]:
        actions.append("Ninja.")
    actions += [
        "Conclave if your hand has an Action other than Conclave whose name is not already in play.",
        "Watchtower if your hand has five or fewer cards.",
        "Stables if your hand contains a Treasure.",
        "Innkeeper, then Silk Merchant, then Ninja.",
        "Catapult if your hand contains a card selected by the trashing instructions below.",
        "Conclave. Otherwise play no Action.",
    ]
    trash = ["Curse, then Estate."]
    if p["curse_silver"]:
        trash.append("Rocks, then Silver, while Curses remain in the supply.")
    trash += [
        f"Copper while you own more than {p['keep_copper']} {'copy' if p['keep_copper'] == 1 else 'copies'}.",
        "Silk Merchant while you own more than one and Curses remain in the supply.",
        "Otherwise trash nothing.",
    ]
    return {
        "choose_gain": DecisionInstructions(
            opening_text + "After turn two, take the first available option below; purchases must also be affordable.",
            tuple(gains),
        ),
        "choose_action": DecisionInstructions(
            "For each Action choice, use the first available option in this order.", tuple(actions),
        ),
        "choose_trash": DecisionInstructions(
            "Trash the first eligible card in this order.", tuple(trash),
        ),
        "choose_treasure_to_discard_for_stables": DecisionInstructions(
            "Choose whether and what to discard for Stables.",
            (
                "Discard nothing if both your deck and discard pile are empty.",
                "Otherwise discard the first available Treasure in this order: Copper, Rocks, Silver, Figurine, Pendant, Gold, Platinum.",
            ),
        ),
        "choose_cards_to_discard": DecisionInstructions(
            "Discard the required number of cards, starting with the lowest-value group. Break ties by their order among the offered cards.",
            (
                "Curse first; then Estate, Duchy, Province and Colony.",
                "Stables with no Treasure among the offered cards; then Copper; then cards not named in these instructions.",
                "Silver and Ninja; then Pendant and Catapult; then Gold, Figurine and Innkeeper.",
                "Silk Merchant; then Platinum and Conclave; then Harbor Village and Stables with a Treasure available; keep Watchtower longest.",
            ),
        ),
        "choose_card_modes": DecisionInstructions(
            "Choose Innkeeper's mode from your current hand.",
            (
                "Draw three and discard three if you have at least two Victory cards or Curses in total, or at most two cards in hand.",
                "Otherwise choose its one-card mode. For other cards, use the supplied default modes.",
            ),
        ),
        "choose_watchtower_reaction": DecisionInstructions(
            "When Watchtower can react to a gain, use these rules in order.",
            (
                "Trash a gained Curse, except keep your first Curse when at most one Colony remains.",
                "Leave gained Victory cards and Copper where they were gained.",
                "Put any other gained card on top of your deck.",
            ),
        ),
    }


# Keys identify the class that implements the hook, including its module.
# StrategyLoader imports modules afresh, so Python class identity is not stable.
_PROVIDERS = {
    "dominion.strategy.strategies.stables_ninja_museum.StablesNinjaMuseum": _stables_ninja_museum,
}


def decision_instructions(strategy, method_name: str) -> DecisionInstructions | None:
    method = getattr(strategy, method_name)
    owner = f"{getattr(method, '__module__', '')}.{getattr(method, '__qualname__', '').rsplit('.', 1)[0]}"
    provider = _PROVIDERS.get(owner)
    return provider(strategy).get(method_name) if provider else None
