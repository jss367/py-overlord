"""Expanded cleanup decisions; the original search policy stays reproducible."""

from collections import Counter
import copy
import random

from dominion.strategy.enhanced_strategy import EnhancedStrategy
from generated_strategies.lucky_coin_ruins import RUINS, LuckyCoinRuins


class LuckyCoinCleanup(LuckyCoinRuins):
    def __init__(self, *, cleanup=None, **kwargs):
        super().__init__(**kwargs)
        self.cleanup = dict(
            trigger="fallback",
            reserve="none",
            double_shrine=False,
            spice_mode="cards",
            spice_silver=False,
            free_shrine=False,
            hold_copper=False,
            mining_first=False,
        )
        self.cleanup.update(cleanup or {})

    @staticmethod
    def armed(p):
        return any(getattr(c, "shrine_armed", False) for c in p.duration)

    def junk(self, p):
        return [c for c in p.hand if c.name in (*RUINS, "Curse", "Estate", "Copper")]

    def choose_action(self, s, p, choices):
        """Reserve junk for armed Shrines and play useful cleanup before terminals."""
        h = Counter(c.name for c in p.hand)
        junk = self.junk(p)
        useful = bool(junk) and (
            h["Lucky Coin"]
            or p.coins + sum(c.stats.coins for c in p.hand if c.is_treasure) >= 2
        )
        names = ["Daimyo"]
        if (
            p.daimyo_pending
            and self.cleanup["double_shrine"]
            and len(junk) >= 3
            and useful
        ):
            names.append("Secluded Shrine")
        names += ["Lost City", "Tea House", "Mining Road", "Warlord"]
        if h["Copper"] or (self.cleanup["spice_silver"] and h["Silver"]):
            names.append("Spice Merchant")
        if useful:
            names.append("Secluded Shrine")
        names += [
            "Highwayman",
            "Change",
            "Battle Plan",
            "Archer",
            "Fool",
            "Secluded Shrine",
        ]
        if not self.armed(p):
            names += [
                "Ruined Village",
                "Ruined Library",
                "Abandoned Mine",
                "Ruined Market",
                "Survivors",
            ]
        return self.pick(choices, names)

    def choose_gain(self, s, p, choices):
        """Consider an immediate Treasure gain to convert an armed Shrine into trashes."""
        normal = super().choose_gain(s, p, choices)
        if s.phase != "buy" or not self.armed(p) or not self.junk(p):
            return normal
        if normal is not None and normal.name in ("Province", "Duchy", "Estate"):
            return normal
        ruins = sum(c.name in RUINS or c.name in ("Curse", "Estate") for c in p.hand)
        trigger = self.cleanup["trigger"]
        if trigger == "silver" and ruins >= 2:
            return self.pick(choices, ["Silver", "Copper"]) or normal
        if trigger == "copper" and ruins >= 2:
            return self.pick(choices, ["Copper"]) or normal
        if normal is not None and normal.name in (
            "Banquet",
            "Silver",
            "Gold",
            "Copper",
        ):
            return normal
        if normal is None:
            return self.pick(choices, ["Silver", "Copper"])
        return normal

    def choose_free_gain(self, s, p, choices, context):
        """Banquet develops income or draw; it need not acquire the cleanup card first."""
        if context.source == "Banquet":
            names = [n for n in self.engine_order(s, p) if n != "Secluded Shrine"]
            return self.pick(
                choices,
                names
                + [
                    "Tea House",
                    "Lost City",
                    "Highwayman",
                    "Mining Road",
                    "Silver",
                    "Secluded Shrine",
                ],
            )
        return super().choose_free_gain(s, p, choices, context)

    def choose_kind_emperor_gain(self, s, p, choices):
        """Optionally add the first Shrine free when there is junk and no collision."""
        if self.cleanup["free_shrine"] and not p.count_in_deck("Secluded Shrine"):
            h = Counter(c.name for c in p.hand)
            timed = self.cleanup["free_shrine"] != "coin" or (
                h["Lucky Coin"] and sum(c.name in RUINS for c in p.hand) >= 2
            )
            if (
                timed
                and len(self.junk(p)) >= 2
                and (h["Lost City"] or not h["Highwayman"])
                and not self.armed(p)
            ):
                target = self.pick(choices, ["Secluded Shrine"])
                if target:
                    return target
        return super().choose_kind_emperor_gain(s, p, choices)

    def copper_hold_plan(self, s, p):
        """Keep Coppers only when a visible Buy-phase rollout trashes more junk
        while preserving all non-Copper purchases and debt payments.

        Only remaining Copper plays and this Buy phase are simulated. No
        future turn or hidden draw is scored; RNG state is restored.
        """
        coppers = [c for c in p.hand if c.name == "Copper"]
        charges = sum(getattr(c, "shrine_charges", 0) for c in p.duration)
        if not charges or not coppers:
            return 0
        player_index = s.players.index(p)
        rng_state = random.getstate()

        def roll(held):
            random.setstate(rng_state)
            clone = copy.deepcopy(s)
            player = clone.players[player_index]
            before = len(player.bought_this_turn)
            cards = [c for c in player.hand if c.name == "Copper"]
            for card in cards[: len(cards) - held]:
                if clone.move_card_from_hand_to_play(player, card):
                    clone.play_treasure_indirectly(player, card)
            clone.phase = "buy"
            clone.handle_buy_phase()
            counts = Counter(c.name for c in player.all_cards())
            return dict(
                purchases=[
                    n for n in player.bought_this_turn[before:] if n != "Copper"
                ],
                debt=player.debt,
                coppers=counts["Copper"],
                ruins=sum(counts[n] for n in RUINS),
                ended=clone._normal_game_end_reached(),
            )

        try:
            baseline = roll(0)
            best = baseline
            chosen = 0
            for held in range(1, min(len(coppers), 2 * charges) + 1):
                candidate = roll(held)
                if (
                    candidate["purchases"] == baseline["purchases"]
                    and candidate["debt"] <= baseline["debt"]
                    and candidate["ruins"] <= baseline["ruins"]
                    and candidate["ended"] == baseline["ended"]
                    and candidate["coppers"] < best["coppers"]
                ):
                    chosen, best = held, candidate
            return chosen
        finally:
            random.setstate(rng_state)

    def choose_treasure(self, s, p, choices):
        """Leave surplus Coppers in hand for Shrine's Buy-phase trashing.

        Lucky Coin can trigger Shrine before other Treasures are played.
        If only Coppers remain, compare playing them with holding them for
        a later gain, preserving the normal purchase sequence.
        """
        treasures = [c for c in choices if c is not None]
        if (
            self.cleanup["hold_copper"]
            and self.armed(p)
            and treasures
            and all(c.name == "Copper" for c in treasures)
        ):
            held = self.copper_hold_plan(s, p)
            if held >= len(treasures):
                return None
        return super().choose_treasure(s, p, choices)

    def choose_gain_effect(self, s, p, gained_card, choices):
        """Optionally play Mining Road's gained Treasure before choosing trashes."""
        if self.cleanup["mining_first"]:
            road = next((e for e in choices if e.kind == "mining_road"), None)
            if road is not None:
                return road
        return super().choose_gain_effect(s, p, gained_card, choices)

    def choose_trash(self, s, p, choices):
        """Trash Ruins before Copper and optionally preserve a purchase breakpoint."""
        result = self.pick(
            choices,
            [
                "Curse",
                "Survivors",
                "Ruined Market",
                "Ruined Village",
                "Ruined Library",
                "Abandoned Mine",
                "Estate",
            ],
        )
        if result:
            return result
        copper = self.pick(choices, ["Copper"])
        if copper:
            if self.cleanup["hold_copper"] and s.phase == "buy":
                # After a buy, a Treasure left in hand cannot be played for
                # income; trashing it cannot reduce spendable coins.
                return copper
            income = p.coins + sum(c.stats.coins for c in p.hand if c.is_treasure)
            reserve = self.cleanup["reserve"]
            breakpoint = (
                (8 if income >= 8 else 5 if income >= 5 else 3 if income >= 3 else 0)
                if reserve == "breakpoints"
                else 3
                if reserve == "three"
                else 0
            )
            if s.phase == "buy" and p.buys == 0:
                breakpoint = 0
            if income - 1 >= breakpoint:
                return copper
        return None if None in choices else super().choose_trash(s, p, choices)

    def choose_treasure_to_trash_for_spice_merchant(self, s, p, choices):
        """Trash Copper, with optional Silver fuel once Tea House income exists."""
        names = ["Copper"]
        if self.cleanup["spice_silver"] and p.count_in_deck("Tea House") >= 2:
            names.append("Silver")
        return self.pick(choices, names)

    def choose_spice_merchant_mode(self, s, p):
        """Compare draw with immediate income or a needed additional Buy."""
        mode = self.cleanup["spice_mode"]
        if mode == "coins":
            return "coins"
        if mode == "adaptive":
            income = p.coins + sum(c.stats.coins for c in p.hand if c.is_treasure)
            actions = [c for c in p.hand if c.is_action and c.name not in RUINS]
            if not actions and (
                income < 8 <= income + 2 or income >= 8 and p.buys == 1
            ):
                return "coins"
        return "cards"


def create_lucky_coin_shrine_cleanup() -> EnhancedStrategy:
    """Historical Shrine candidate; revalidate with Mining Road granting $2."""
    strategy = LuckyCoinCleanup(
        opening="Secluded Shrine",
        shrine=1,
        lost=0,
        highway=1,
        banquet=True,
        daimyo=4,
        green=1,
        spice=1,
        cleanup=dict(
            trigger="fallback",
            reserve="breakpoints",
            double_shrine=False,
            hold_copper=True,
            mining_first=True,
        ),
    )
    strategy.name = "Lucky Coin Shrine Cleanup"
    strategy.description = "Experimental Shrine/Spice Merchant candidate; historical results used incorrect Mining Road income and need revalidation."
    return strategy
