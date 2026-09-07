"""Dedicated Mine and Guildhall policies, with parameters for focused search."""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy
from generated_strategies.tea_house_kind_emperor import TeaHouseEmperor


SETUPS = {
    "tea_mine_guild": ["Tea House", "Mine", "Guildhall", "Tea House"],
    "tea_guild_mine": ["Tea House", "Guildhall", "Mine", "Tea House"],
    "mine_guild_tea": ["Mine", "Guildhall", "Tea House", "Tea House"],
    "guild_mine_tea": ["Guildhall", "Mine", "Tea House", "Tea House"],
    "two_tea_mine_guild": ["Tea House", "Tea House", "Mine", "Guildhall"],
    "free_mine": ["Tea House", "Tea House", "Guildhall"],
    "guild_free_mine": ["Guildhall", "Tea House", "Tea House"],
    "mastermind_mine": ["Tea House", "Mastermind", "Mine", "Guildhall", "Tea House"],
    "mine_mastermind_guild": ["Mine", "Mastermind", "Guildhall"],
    "mine_guild": ["Mine", "Guildhall"],
}


class MineGuildhall(TeaHouseEmperor):
    def __init__(
        self,
        *,
        setup="tea_mine_guild",
        opening="Fortune Hunter",
        mines=1,
        envoys=1,
        teas=4,
        masterminds=0,
        free="adaptive",
        upgrade="copper",
        triple="mine",
        green_turn=6,
        silvers=2,
        buried=0,
        guildhall=True,
        mine_order="late",
        copper_buys=False,
    ):
        super().__init__(opening=opening, envoy=envoys, silvers=silvers)
        self.name = "Mine and Guildhall Engine"
        self.description = "Upgrade Treasures with Mine, earn Coffers with Guildhall, and use Kind Emperor for engine pieces."
        self.combo_params = dict(
            setup=setup,
            opening=opening,
            mines=mines,
            envoys=envoys,
            teas=teas,
            masterminds=masterminds,
            free=free,
            upgrade=upgrade,
            triple=triple,
            green_turn=green_turn,
            silvers=silvers,
            buried=buried,
            guildhall=guildhall,
            mine_order=mine_order,
            copper_buys=copper_buys,
        )
        self.mine_gains = Counter()
        self.mastermind_targets = Counter()

    def choose_mine_treasure(self, state, player, choices):
        """Upgrade weak Treasures before recycling Gold for a Guildhall trigger."""
        mode = self.combo_params["upgrade"]
        order = ["Copper", "Anvil", "Silver", "Buried Treasure", "Gold"]
        if mode == "silver":
            order = ["Silver", "Copper", "Anvil", "Buried Treasure", "Gold"]
        elif mode == "buried":
            order = ["Silver", "Anvil", "Copper", "Gold", "Buried Treasure"]
        elif mode == "gold":
            order = ["Gold", "Silver", "Copper", "Anvil", "Buried Treasure"]
        has_guild = any(p.name == "Guildhall" for p in player.projects)
        candidates = [c for c in choices if c.name != "Gold" or has_guild]
        chosen = self.pick(candidates, order)
        self.mine_source = chosen.name if chosen else None
        return chosen

    def choose_mine_gain(self, state, player, choices):
        """Choose Gold or a self-playing Buried Treasure after the upgrade."""
        p = self.combo_params
        names = ["Gold", "Silver", "Anvil", "Copper"]
        if p["upgrade"] == "buried" and player.count("Buried Treasure") < p["buried"]:
            names.insert(0, "Buried Treasure")
        chosen = self.pick(choices, names)
        if chosen:
            self.mine_gains[
                f"{getattr(self, 'mine_source', 'unknown')} -> {chosen.name}"
            ] += 1
        return chosen

    def choose_mastermind_action(self, state, player, choices):
        """Explicitly test triple Mine, triple draw, and triple Tea House."""
        names = [
            "City Quarter",
            "Tea House",
            "Imperial Envoy",
            "Mine",
            "Courier",
            "Fortune Hunter",
        ]
        if self.combo_params["triple"] == "mine" and any(
            c.is_treasure for c in player.hand
        ):
            names.insert(0, "Mine")
        elif self.combo_params["triple"] == "tea":
            names.insert(0, "Tea House")
        chosen = self.pick(choices, names)
        if chosen:
            self.mastermind_targets[chosen.name] += 1
        return chosen

    def choose_kind_emperor_gain(self, state, player, choices):
        """Use free gains for Mines and Masterminds as well as villages and draw."""
        p = self.combo_params
        counts = Counter(c.name for c in player.all_cards())
        hand = Counter(c.name for c in player.hand)
        names = []
        if p["free"] == "mine_first" and counts["Mine"] < p["mines"]:
            names.append("Mine")
        if p["free"] == "mastermind_first" and counts["Mastermind"] < p["masterminds"]:
            names.append("Mastermind")
        if not hand["City Quarter"]:
            names.append("City Quarter")
        if p["free"] == "draw_first" and counts["Imperial Envoy"] < p["envoys"]:
            names.append("Imperial Envoy")
        if counts["Mine"] < p["mines"]:
            names.append("Mine")
        if counts["Mastermind"] < p["masterminds"]:
            names.append("Mastermind")
        if counts["Imperial Envoy"] < p["envoys"]:
            names.append("Imperial Envoy")
        names += [
            "Tea House",
            "City Quarter",
            "Imperial Envoy",
            "Fortune Hunter",
            "Courier",
            "Mine",
            "Mastermind",
        ]
        return self.pick(choices, names)

    def choose_action(self, state, player, choices):
        p = self.combo_params
        order = [
            "City Quarter",
            "Tea House",
            "Courier",
            "Imperial Envoy",
            "Mine",
            "Mastermind",
            "Fortune Hunter",
        ]
        if p["mine_order"] == "early":
            order = [
                "City Quarter",
                "Tea House",
                "Mine",
                "Courier",
                "Imperial Envoy",
                "Mastermind",
                "Fortune Hunter",
            ]
        # Avoid spending an Action on a Mine that cannot upgrade anything.
        choices = [
            c
            for c in choices
            if c is None or c.name != "Mine" or any(t.is_treasure for t in player.hand)
        ]
        return self.pick(choices, order)

    def choose_courier_card(self, state, player, choices):
        names = [
            "City Quarter",
            "Tea House",
            "Courier",
            "Imperial Envoy",
            "Mine",
            "Mastermind",
            "Gold",
            "Fortune Hunter",
            "Silver",
            "Buried Treasure",
            "Copper",
            "Anvil",
        ]
        return self.pick(choices, names)

    def choose_gain(self, state, player, choices):
        """Acquire the selected setup, then balance engine pieces with points."""
        p = self.combo_params
        counts = Counter(c.name for c in player.all_cards())
        guild = any(x.name == "Guildhall" for x in player.projects)
        counts["Guildhall"] = int(guild)
        names = []
        if player.turns_taken >= p["green_turn"] or state.supply["Province"] <= 4:
            names.append("Province")
        if state.supply["Province"] <= 3:
            names.append("Duchy")
        if state.supply["Province"] <= 1:
            names.append("Estate")
        required = Counter()
        for card in SETUPS[p["setup"]]:
            if card == "Guildhall" and not p["guildhall"]:
                continue
            if card == "Mine" and not p["mines"]:
                continue
            required[card] += 1
            if counts[card] < required[card]:
                names.append(card)
        if counts["City Quarter"]:
            for card, cap in [
                ("Imperial Envoy", p["envoys"]),
                ("Mine", p["mines"]),
                ("Mastermind", p["masterminds"]),
            ]:
                if counts[card] < cap:
                    names.append(card)
        if counts["Tea House"] < p["teas"]:
            names.append("Tea House")
        if counts["Buried Treasure"] < p["buried"]:
            names.append("Buried Treasure")
        names += ["Province"]
        if counts["Gold"] < 2:
            names.append("Gold")
        if not counts[p["opening"]]:
            names.append(p["opening"])
        if counts["Silver"] < p["silvers"]:
            names.append("Silver")
        if not state.supply["Tea House"] and state.supply["Province"] <= 5:
            names.append("Duchy")
        if p["copper_buys"] and guild and player.buys > 1 and counts["Copper"] < 7:
            names.append("Copper")
        return self.pick(choices, names)


def create_mine_and_guildhall_engine() -> EnhancedStrategy:
    return MineGuildhall(
        setup="two_tea_mine_guild",
        free="mine_first",
        silvers=3,
        buried=0,
        envoys=2,
        upgrade="silver",
    )
