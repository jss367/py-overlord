"""Strategies for Tea House / Kind Emperor; parameters support local search."""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TeaHouseEmperor(EnhancedStrategy):
    def __init__(
        self,
        *,
        opening="Courier",
        silvers=2,
        tea_target=4,
        envoy=1,
        mastermind=0,
        buried=0,
        guildhall=False,
        mine=0,
        anvil=0,
        green=4,
        scoring="Province",
        free="adaptive",
        buy_city=False,
    ):
        super().__init__()
        self.name = "Tea House and Kind Emperor Engine"
        self.description = "Activate Kind Emperor, gain City Quarters to hand, and build Tea House income."
        self.params = dict(
            opening=opening,
            silvers=silvers,
            tea_target=tea_target,
            envoy=envoy,
            mastermind=mastermind,
            buried=buried,
            guildhall=guildhall,
            mine=mine,
            anvil=anvil,
            green=green,
            scoring=scoring,
            free=free,
            buy_city=buy_city,
        )
        self.action_priority = [
            PriorityRule(n)
            for n in [
                "City Quarter",
                "Tea House",
                "Courier",
                "Imperial Envoy",
                "Mastermind",
                "Fortune Hunter",
                "Mine",
            ]
        ]
        self.treasure_priority = [
            PriorityRule(n)
            for n in ["Anvil", "Gold", "Silver", "Copper", "Buried Treasure"]
        ]
        self.gain_priority = [
            PriorityRule(n)
            for n in [
                "Province",
                "Tea House",
                "City Quarter",
                "Imperial Envoy",
                "Mastermind",
                "Buried Treasure",
                "Courier",
                "Fortune Hunter",
                "Mine",
                "Anvil",
                "Guildhall",
                "Duchy",
                "Duke",
                "Gold",
                "Silver",
                "Estate",
            ]
        ]

    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    def choose_kind_emperor_gain(self, state, player, choices):
        """Gain a village when absent from hand, then draw and income."""
        counts = Counter(c.name for c in player.all_cards())
        hand = Counter(c.name for c in player.hand)
        p = self.params
        if p["free"] == "tea":
            names = ["Tea House", "City Quarter", "Imperial Envoy"]
        elif p["free"] == "city":
            names = ["City Quarter", "Tea House", "Imperial Envoy"]
        else:
            names = []
            if not hand["City Quarter"]:
                names.append("City Quarter")
            if counts["Imperial Envoy"] < p["envoy"]:
                names.append("Imperial Envoy")
            if counts["Mastermind"] < p["mastermind"]:
                names.append("Mastermind")
            names += ["Tea House", "City Quarter", "Imperial Envoy"]
        return self.pick(
            choices, names + ["Courier", "Fortune Hunter", "Mastermind", "Mine"]
        )

    def choose_action(self, state, player, choices):
        # Outside the main Action phase, Mastermind offers a free triple play.
        if not getattr(state, "_choosing_main_action_phase", False) and any(
            c is not None and c.name == "Mastermind" for c in player.duration
        ):
            actions = sum(c.is_action for c in player.hand)
            order = (["City Quarter"] if actions >= 3 else []) + [
                "Tea House",
                "City Quarter",
                "Imperial Envoy",
                "Courier",
                "Fortune Hunter",
                "Mine",
            ]
            return self.pick(choices, order)
        return super().choose_action(state, player, choices)

    def choose_courier_target(self, state, player, choices):
        """Recover an Action that keeps the turn going before taking money."""
        actions = sum(c.is_action for c in player.hand)
        names = ["City Quarter"] if player.actions < 1 or actions >= 2 else []
        names += [
            "Tea House",
            "Courier",
            "Imperial Envoy",
            "City Quarter",
            "Mastermind",
            "Gold",
            "Fortune Hunter",
            "Silver",
            "Buried Treasure",
            "Copper",
            "Anvil",
            "Mine",
        ]
        return self.pick(choices, names)

    def choose_gain(self, state, player, choices):
        """Buy early Provinces, up to four Tea Houses, and two draw cards.

        Counts and caps are configurable for reproducible comparison. The
        gain_priority list records references; this hook is the buy policy.
        """
        counts = Counter(c.name for c in player.all_cards())
        p = self.params
        available = {c.name: c for c in choices if c is not None}
        # Mine's gain menu contains only Treasures.
        if (
            available
            and all(c.is_treasure for c in available.values())
            and state.phase != "buy"
        ):
            return self.pick(
                choices, ["Gold", "Buried Treasure", "Silver", "Anvil", "Copper"]
            )
        names = []
        provinces = state.supply.get("Province", 8)
        if player.turns_taken <= 2:
            if "Tea House" in available:
                return available["Tea House"]
            if p["opening"] != "Silver" and not counts[p["opening"]]:
                names.append(p["opening"])
            names.append("Silver")
            return self.pick(choices, names)
        green = counts["Tea House"] >= p["green"] or provinces <= 4
        if p["scoring"] == "Duke" and (green or player.turns_taken >= 10):
            names += (
                ["Duke", "Duchy"]
                if counts["Duchy"] >= 4 and counts["Duke"] < counts["Duchy"] - 2
                else ["Duchy", "Duke"]
            )
        if green:
            names.append("Province")
        if provinces <= 3:
            names += ["Duchy", "Duke"] if counts["Duchy"] < 4 else ["Duke", "Duchy"]
        if provinces <= 1:
            names.append("Estate")
        if counts["Tea House"] < min(2, p["tea_target"]):
            names.append("Tea House")
        if p["guildhall"] and not any(x.name == "Guildhall" for x in player.projects):
            names.append("Guildhall")
        for card, cap in [
            ("Buried Treasure", p["buried"]),
            ("Anvil", p["anvil"]),
            ("Mine", p["mine"]),
        ]:
            if counts[card] < cap:
                names.append(card)
        if p["buy_city"] and not counts["City Quarter"] and counts["Tea House"] >= 2:
            names.append("City Quarter")
        if counts["City Quarter"]:
            for card, cap in [
                ("Imperial Envoy", p["envoy"]),
                ("Mastermind", p["mastermind"]),
            ]:
                if counts[card] < cap:
                    names.append(card)
        if counts["Tea House"] < p["tea_target"]:
            names.append("Tea House")
        names.append("Province")
        if counts["Gold"] < 2:
            names.append("Gold")
        if not counts["Courier"] and p["opening"] == "Courier":
            names.append("Courier")
        if not counts["Fortune Hunter"] and p["opening"] == "Fortune Hunter":
            names.append("Fortune Hunter")
        if counts["Silver"] < p["silvers"]:
            names.append("Silver")
        if not state.supply.get("Tea House", 0) and provinces <= 5:
            names += ["Duchy", "Duke"]
        return self.pick(choices, names)


def create_tea_house_kind_emperor() -> EnhancedStrategy:
    return TeaHouseEmperor(opening="Fortune Hunter", green=1, envoy=2)
