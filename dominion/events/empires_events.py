"""Empires Events."""

from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card

from .base_event import Event


class Triumph(Event):
    """$5, debt 5: Gain an Estate. If you did, +1 VP per card you've gained this turn."""

    def __init__(self):
        super().__init__("Triumph", CardCost(coins=5, debt=5))

    def on_buy(self, game_state, player) -> None:
        if game_state.supply.get("Estate", 0) <= 0:
            return
        cards_gained_before = player.cards_gained_this_turn
        game_state.supply["Estate"] -= 1
        game_state.gain_card(player, get_card("Estate"))
        # Per Empires rule: +1 VP per card gained this turn (Estate counted).
        player.vp_tokens += cards_gained_before + 1


class Annex(Event):
    """8 debt: Don't shuffle. Look through discard, choose all but up to 5,
    put them in your deck. Gain a Duchy."""

    def __init__(self):
        super().__init__("Annex", CardCost(debt=8))

    def on_buy(self, game_state, player) -> None:
        if player.discard:
            # Sort discard so the 5 cheapest stay in discard, rest go to deck
            ordered = sorted(player.discard, key=lambda c: (c.cost.coins, c.name))
            stay = ordered[:5]
            move = ordered[5:]
            player.discard = list(stay)
            # Put the moved cards on top of the deck (no shuffle).
            player.deck.extend(move)

        if game_state.supply.get("Duchy", 0) > 0:
            game_state.supply["Duchy"] -= 1
            game_state.gain_card(player, get_card("Duchy"))


class Donate(Event):
    """8 debt: At end of buy phase, put hand+deck into discard, trash any from
    discard, then put discard into deck and shuffle."""

    def __init__(self):
        super().__init__("Donate", CardCost(debt=8))

    def on_buy(self, game_state, player) -> None:
        # Mark for end-of-buy resolution.
        player.donate_pending = getattr(player, "donate_pending", 0) + 1


class Advance(Event):
    """$0: Trash an Action card from hand; gain an Action costing up to $6."""

    def __init__(self):
        super().__init__("Advance", CardCost(coins=0))

    def on_buy(self, game_state, player) -> None:
        actions_in_hand = [c for c in player.hand if c.is_action]
        if not actions_in_hand:
            return
        chosen = player.ai.choose_card_to_trash(game_state, actions_in_hand + [None])
        if chosen is None or chosen not in actions_in_hand:
            chosen = actions_in_hand[0]
        player.hand.remove(chosen)
        game_state.trash_card(player, chosen)

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.is_action and card.cost.coins <= 6 and card.cost.potions == 0 and card.cost.debt == 0:
                candidates.append(card)
        if candidates:
            candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            gain = candidates[0]
            game_state.supply[gain.name] -= 1
            game_state.gain_card(player, gain)


class Delve(Event):
    """$2: +1 Buy. Gain a Silver."""

    def __init__(self):
        super().__init__("Delve", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        player.buys += 1
        if game_state.supply.get("Silver", 0) > 0:
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))


class Tax(Event):
    """$2: Add 1 debt to a Supply pile (cards from that pile cost $1 more debt
    until next time someone buys a card from it).

    Implementation: cards from a taxed pile cost +D when bought, and the tax
    is removed when bought. The buyer then gains the debt; this matches the
    intent of "+1 Debt is added to a Supply pile" from official rules.
    """

    def __init__(self):
        super().__init__("Tax", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        # Pick the highest-cost non-Curse pile that still has cards. Any
        # opponent will have to take that debt when buying it next.
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0 or name == "Curse":
                continue
            candidates.append(name)
        if not candidates:
            return
        candidates.sort(key=lambda n: (get_card(n).cost.coins, n), reverse=True)
        target = candidates[0]
        game_state.tax_tokens[target] = game_state.tax_tokens.get(target, 0) + 1


class Banquet(Event):
    """$3: Gain 2 Coppers and a non-Victory card costing up to $5."""

    def __init__(self):
        super().__init__("Banquet", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        for _ in range(2):
            if game_state.supply.get("Copper", 0) <= 0:
                break
            game_state.supply["Copper"] -= 1
            game_state.gain_card(player, get_card("Copper"))

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.is_victory:
                continue
            if card.cost.coins > 5 or card.cost.potions > 0 or card.cost.debt > 0:
                continue
            candidates.append(card)
        if candidates:
            candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            gain = candidates[0]
            game_state.supply[gain.name] -= 1
            game_state.gain_card(player, gain)


class Ritual(Event):
    """$4: Gain a Curse. If you did, trash a card from hand. +1 VP per $1 it cost."""

    def __init__(self):
        super().__init__("Ritual", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        if game_state.supply.get("Curse", 0) <= 0:
            return
        game_state.supply["Curse"] -= 1
        game_state.gain_card(player, get_card("Curse"))

        if not player.hand:
            return
        # Pick the highest-coin-cost non-Curse for max VP.
        candidates = [c for c in player.hand if c.name != "Curse"]
        if not candidates:
            return
        chosen = max(candidates, key=lambda c: (c.cost.coins, c.name))
        player.hand.remove(chosen)
        game_state.trash_card(player, chosen)
        player.vp_tokens += chosen.cost.coins


class SaltTheEarth(Event):
    """$4: +1 VP. Trash a Victory card from the Supply."""

    def __init__(self):
        super().__init__("Salt the Earth", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        player.vp_tokens += 1
        # Prefer trashing a Province (highest VP cards from supply pressure).
        for preferred in ("Province", "Duchy", "Estate"):
            if game_state.supply.get(preferred, 0) > 0:
                game_state.supply[preferred] -= 1
                game_state.trash.append(get_card(preferred))
                return

        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.is_victory:
                game_state.supply[name] -= 1
                game_state.trash.append(card)
                return


class Wedding(Event):
    """$4, debt 3: +1 VP. Gain a Gold."""

    def __init__(self):
        super().__init__("Wedding", CardCost(coins=4, debt=3))

    def on_buy(self, game_state, player) -> None:
        player.vp_tokens += 1
        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))


class Windfall(Event):
    """$5: If your deck and discard are empty, gain 3 Golds."""

    def __init__(self):
        super().__init__("Windfall", CardCost(coins=5))

    def on_buy(self, game_state, player) -> None:
        if player.deck or player.discard:
            return
        for _ in range(3):
            if game_state.supply.get("Gold", 0) <= 0:
                break
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))


class Conquest(Event):
    """$6: Gain 2 Silvers. +1 VP per Silver you've gained this turn."""

    def __init__(self):
        super().__init__("Conquest", CardCost(coins=6))

    def on_buy(self, game_state, player) -> None:
        # Count Silvers gained earlier this turn; the +1 VP per silver applies
        # after gaining the 2 from this event (per Wiki: includes silvers from
        # this event itself).
        for _ in range(2):
            if game_state.supply.get("Silver", 0) <= 0:
                break
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))

        silvers_this_turn = sum(
            1 for name in player.gained_cards_this_turn if name == "Silver"
        )
        player.vp_tokens += silvers_this_turn


class Dominate(Event):
    """$14: Gain a Province. If you did, +9 VP."""

    def __init__(self):
        super().__init__("Dominate", CardCost(coins=14))

    def on_buy(self, game_state, player) -> None:
        if game_state.supply.get("Province", 0) <= 0:
            return
        game_state.supply["Province"] -= 1
        game_state.gain_card(player, get_card("Province"))
        player.vp_tokens += 9
