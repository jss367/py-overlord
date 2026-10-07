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
        actions.append("Ninja, while you have an Action to spare.")
    actions += [
        "Conclave if your hand has an Action other than Conclave whose name is not already in play.",
        "Watchtower if your hand has five or fewer cards and you have an Action to spare.",
        "Stables if your hand contains a Treasure.",
        "Innkeeper.",
        "Watchtower if your hand has five or fewer cards.",
        "Silk Merchant, then Ninja.",
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
            "For each Action choice, use the first available option in this order. "
            "\u201cAn Action to spare\u201d means more than one Action remaining: on your "
            "last Action, anything that refunds one is played before a terminal, so "
            "Watchtower drops below Stables and Innkeeper.",
            tuple(actions),
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


def _hunting_grounds_ghost_ship(strategy) -> dict[str, DecisionInstructions]:
    p = strategy.params
    gains = [
        f"Province from your turn {p['green']}, or with four or fewer Provinces remaining.",
        f"Duchy with {p['duchy']} or fewer Provinces remaining; Estate with one or fewer.",
        f"On your first two turns, your first {p['opening']}.",
    ]
    if p["village_ratio"]:
        gains.append(
            "Farming Village while its count is below "
            f"{p['village_ratio']} times your combined Hunting Grounds, Ghost Ship, "
            "Woodcutter and Bishop count minus one (minimum zero)."
        )
    gains.extend(f"{n} while you own fewer than {cap}." for n, cap in p["targets"] if cap)
    gains.extend([
        f"Gold while you own fewer than {p['gold']}; then Silver while you own fewer than {p['silver']}.",
        "Otherwise pass. Skip Raze purchases once you have no Estates and your Copper count is at or below its retention threshold.",
    ])
    actions = [rule.card_name for rule in strategy.action_priority]
    if p["draw_first"] and "Hunting Grounds" in actions and "Ghost Ship" in actions:
        actions.remove("Hunting Grounds")
        actions.insert(actions.index("Ghost Ship"), "Hunting Grounds")
    return {
        "choose_gain": DecisionInstructions("Take the first available option; purchases must be affordable.", tuple(gains)),
        "choose_action": DecisionInstructions(
            "Play Actions in this order. Skip Apprentice without an acceptable junk target. "
            "Skip Bishop too, unless its fodder option is enabled and Hunting Grounds, Cache or Gold is in hand.",
            tuple(actions) or ("No planned Action purchases.",),
        ),
        "choose_card_to_raze": DecisionInstructions(
            "Apply the trashing thresholds below, then trash Raze itself.",
            ("Prefer Curse, then Estate, then eligible Copper; otherwise select Raze.",),
        ),
        "choose_card_to_keep_from_raze": DecisionInstructions(
            "Keep one of the cards Raze reveals.",
            ("Use the Action priorities first; otherwise prefer printed coin value, then cost.",),
        ),
        "choose_card_to_topdeck_from_hand": DecisionInstructions(
            "Put the lowest-value card back first; break ties by cost, then name. The same defense is used by all tested opponents.",
            (
                "Victory cards and Curse, then Copper, then Quarry and trashers with no acceptable junk.",
                "Silver; then Woodcutter and duplicate Farming Villages; then Gold and Cache.",
                "Trashers with junk; then your last Farming Village; keep Hunting Grounds, Ghost Ship and Menagerie longest.",
            ),
        ),
        "choose_trash": DecisionInstructions(
            "Trash Curse, then Estate, then eligible Copper. On an opponent's Bishop turn, use your own deck counts and otherwise decline.",
            (
                f"Copper is eligible only above {p['copper_floor']} copies and with more than $5 total printed Treasure value in your deck.",
                "With fodder enabled, next try Hunting Grounds, Cache, then Gold; otherwise a mandatory choice takes the cheapest non-Victory card first.",
                "Raze uses the junk rules, then trashes itself. Apprentice is never deliberately played without junk to trash.",
            ),
        ),
    }


def _collection_imperial_envoy(strategy) -> dict[str, DecisionInstructions]:
    p = strategy.params
    steps = [
        f"Province from your turn {p['green']}, or with two or fewer Provinces left.",
        f"Duchy with {p['duchy']} or fewer Provinces left; Estate with one or fewer.",
        f"On your first two turns, your first {p['opening']}.",
        f"If neither Collection nor Imperial Envoy is owned, prefer {p['first_five']} if its target is positive.",
        f"Swindler up to {p['swindler']} owned copies.",
        f"Imperial Envoy up to {p['envoy']} copies, requiring at least as many Villages plus Ghost Towns as existing Envoys before buying another.",
        f"Collection up to {p['collection']} copies.",
        f"Village up to {p['village']} copies, only while its existing count is no greater than the combined Envoy, Swindler, Sleigh and Merchant Ship count.",
        f"Mystic up to {p['mystic']}; Merchant Ship up to {p['ship']}; Ghost Town up to {p['ghost']}; Sleigh up to {p['sleigh']}.",
    ]
    if p['forts']:
        steps.append("Your first Tent, then Stronghold, Hill Fort and Garrison up to two each, when exposed.")
    if p['farm']:
        order = "Fishmonger, Sleigh, Village, Swindler, Tent" if p['cheap_first'] else "Village, Fishmonger, Sleigh, Swindler, Tent"
        steps.append(f"With at least {p['farm']} Collections played this turn, buy Actions without a copy cap in this order: {order}.")
    steps.extend([
        f"Gold up to {p['gold']}; Silver up to {p['silver']}; Fishmonger up to {p['fish']}.",
        "With three or fewer Provinces left, Duchy then Estate. Otherwise pass.",
    ])
    return {
        "choose_gain": DecisionInstructions("Take the first eligible, available card; purchases must be affordable. Counts include attack gains. Zero targets skip a card.", tuple(steps)),
        "choose_allies_option": DecisionInstructions("Forts rotation.", (
            "Do not rotate." if not p['forts'] else "Rotate with Tent until " + {1: "Garrison", 2: "Hill Fort", 3: "Stronghold"}[p['forts']] + " is exposed.",
            "Use the simulator's supplied defaults for other Allies decisions.",
        )),
        "name_card_for_mystic": DecisionInstructions("Name the most common card in the remaining deck, including Copper.", (
            "Infer composition from owned cards minus visible zones; do not inspect hidden order. If the deck is empty, use the discard composition. Break ties alphabetically.",
        )),
        "choose_swindler_replacement": DecisionInstructions("Give the opponent the first legal exposed card in this order.", (
            "Curse, Estate, Duchy, Tent, Silver, Fishmonger, Merchant Ship, Mystic, Swindler, Ghost Town, Village, Garrison, Hill Fort, Sleigh, Gold, Stronghold, Imperial Envoy, Collection, Province, Copper.",
            "If none of those is offered, choose the first offered card.",
        )),
    }


def _shepherd_tragic_hero(strategy) -> dict[str, DecisionInstructions]:
    p = strategy.params
    targets = [("Shepherd", "shepherd"), ("Tragic Hero", "hero"),
               ("Cobbler", "cobbler"), ("Exorcist", "exorcist"),
               ("Crypt", "crypt"), ("Secret Cave", "cave"),
               ("Faithful Hound", "hound"), ("Guardian", "guardian"),
               ("Herbalist", "herbalist")]
    if p["priority"] == "night":
        targets.sort(key=lambda t: t[0] not in {"Cobbler", "Exorcist", "Crypt"})
    elif p["priority"] == "cave":
        targets.sort(key=lambda t: t[0] not in {"Secret Cave", "Faithful Hound"})
    buys = [
        f"Province from your turn {p['green']}, or with four or fewer Provinces left.",
        f"Duchy at {p['duchy']} or fewer Provinces; Estate at {p['estate']} or fewer.",
        f"On turns one and two, prefer your first {p['opening']} if its ownership target is positive.",
    ]
    if p["monastery"] and p["monastery_timing"] == "early":
        buys.append(f"Through turn eight, Monastery up to {p['monastery']} owned.")
    if p["priority"] == "money":
        buys.append(f"Gold up to {p['gold']} owned.")
    buys += [f"{name} up to {p[key]} owned." for name, key in targets if p[key]]
    buys += [
        "Require at least one Gold before buying Crypt. Additional Shepherds require at least twice as many Victory cards as Shepherds currently owned.",
        f"Gold up to {p['gold']} owned, then Silver up to {p['silver']} owned.",
    ]
    if p["monastery"] and p["monastery_timing"] == "spare":
        buys.append(f"Through turn twelve, Monastery up to {p['monastery']} owned.")
    buys.append(f"Estate up to {p['extra_estates']} owned if you own Shepherd. Otherwise pass.")
    actions = DecisionInstructions("Take the first legal option in this order.", (
        "Wish, Will-o'-Wisp, Shepherd when holding a Victory card, Secret Cave, Shepherd, Imp, Tragic Hero, Faithful Hound, Herbalist.",
    ))
    return {
        "choose_gain": DecisionInstructions("Take the first affordable available option; targets count cards currently owned, so replace trashed Tragic Heroes.", tuple(buys)),
        "choose_action": actions,
        "choose_imp_action": actions,
        "choose_card_to_gain_to_hand": (
            _cobbler_shepherd(strategy)["choose_card_to_gain_to_hand"]
            if p["cobbler_shepherds"] is not None
            else DecisionInstructions("Use the buying priorities for Cobbler and Wish.", (
                "If no target remains, take Gold, Silver, Estate, then Copper, in that order.",
            ))
        ),
        "choose_treasure": DecisionInstructions("Play Gold, Silver, Pasture, Copper, then Magic Lamp.", (
            f"With Exorcist in hand and fewer than {p['imps']} Imps, reserve one Silver for trashing.",
            "When holding Magic Lamp, first play one of each other available Treasure name not already in play; play Lamp before duplicate Treasures.",
        )),
        "choose_night": DecisionInstructions("Play Night cards in this order.", (
            "Guardian, Cobbler, Exorcist only with an eligible trash target, Monastery, Crypt, Ghost.",
        )),
        "choose_trash": DecisionInstructions("Exorcist uses the first available target below.", (
            "Curse; Estate only if Estate retention is disabled and more than three Provinces remain.",
            f"Silver, then Secret Cave, while you have fewer than {p['imps']} Imps.",
            f"Cobbler, Crypt, Tragic Hero, then Gold while you have fewer than {p['ghosts']} Ghosts.",
            "Copper; then an Estate above both the Shepherd count and the retained floor (three with retention enabled, otherwise zero). Otherwise skip.",
        )),
        "choose_card_to_gain_for_exorcist": DecisionInstructions("Choose a legal Spirit.", (
            f"Ghost first until {p['ghosts']} owned; otherwise Imp, Will-o'-Wisp, Ghost.",
        )),
        "choose_cards_to_trash_for_monastery": DecisionInstructions(f"Estate retention is {'enabled' if p['keep_estates'] else 'disabled'}.", (
            "Trash Curse, then Copper. Trash Copper only when owned Gold and Silver provide at least three coins in total.",
            "With retention disabled and more than three Provinces left, trash Estates after Copper. Stop when eligible junk runs out.",
        )),
        "choose_secret_cave_discards": DecisionInstructions("Discard three eligible cards if available; otherwise decline.", (
            "Eligible cards are Faithful Hound, Curse, Estate, Duchy and Province, in hand order." + (" Add Coppers after those cards." if p['cave_mode'] else ""),
        )),
        "choose_treasures_to_set_aside_for_crypt": DecisionInstructions("Set aside eligible played Treasures.", (
            f"Set aside each Treasure with printed coin value at least {p['crypt_min']}; return the most expensive available Treasure each turn.",
        )),
    }


def _cobbler_shepherd(strategy) -> dict[str, DecisionInstructions]:
    p = strategy.params
    steps = [
        f"At {p['estate']} or fewer Provinces remaining, gain Estate first.",
        f"Before the draw target, gain Silver until {p['cobbler_silver']} owned.",
        f"Gain Shepherd until {p['cobbler_shepherds']} owned."
        + (" Only do this when holding a Victory card and no Shepherd."
           if p['cobbler_adaptive'] else ""),
        f"Then gain Estate until {p['cobbler_estates']} owned.",
        "Otherwise take Silver, Estate, Shepherd, then Copper, in that order.",
        "Wishes use the ordinary buying priorities, with Gold, Silver, Estate, Copper as fallback.",
    ]
    return {
        "choose_card_to_gain_to_hand": DecisionInstructions(
            "Cobbler has separate free-gain targets; purchased Shepherds use the buying target.",
            tuple(steps),
        ),
    }


# Keys identify the class that implements the hook, including its module.
# StrategyLoader imports modules afresh, so Python class identity is not stable.
_PROVIDERS = {
    "dominion.strategy.strategies.shepherd_tragic_hero.ShepherdTragicHero": _shepherd_tragic_hero,
    "dominion.strategy.strategies.collection_imperial_envoy.CollectionImperialEnvoy": _collection_imperial_envoy,
    "dominion.strategy.strategies.hunting_grounds_ghost_ship.HuntingGroundsPolicy": _hunting_grounds_ghost_ship,
    "dominion.strategy.strategies.stables_ninja_museum.StablesNinjaMuseum": _stables_ninja_museum,
}


def decision_instructions(strategy, method_name: str) -> DecisionInstructions | None:
    method = getattr(strategy, method_name)
    owner = f"{getattr(method, '__module__', '')}.{getattr(method, '__qualname__', '').rsplit('.', 1)[0]}"
    provider = _PROVIDERS.get(owner)
    return provider(strategy).get(method_name) if provider else None
