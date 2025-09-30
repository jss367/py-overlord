from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class BigMoneySmithyStrategy(EnhancedStrategy):
    """Big Money + Smithy: 1–2 Smithies for burst draw, clean greening rules, no fancy engine pieces."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "BigMoneySmithy"
        self.description = "Big Money with up to two Smithies, disciplined greening, and simple payload"
        self.version = "3.0"

        # Static priorities (engine uses these when it doesn't call choose_gain)
        # Keep simple: play Smithy when seen; treasures in descending value.
        self.gain_priority = []
        self.action_priority = [PriorityRule("Smithy")]
        self.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

    # ------------------------------------------------------------------
    def _provinces_left(self, state) -> int:
        pile = state.supply.get("Province")
        return getattr(pile, "count", 0) if pile else 0

    def _count(self, player, card_name: str) -> int:
        return player.count_in_deck(card_name) if hasattr(player, "count_in_deck") else 0

    def choose_gain(self, state, player, choices):
        """Buy rules tuned for BM+Smithy:
        - Province at 8+
        - Duchy with pressure (<=4 Provinces left) on $5+
        - Estate very late (<=2 Provinces left) on $2+
        - 1–2 Smithies early at exactly $4 (avoid terminal collision spam)
        - Gold at 6+
        - Silver at 3–5 (unless Duchy rule triggered at $5)
        """
        card = {c.name: c for c in choices if c is not None}
        coins = player.coins
        prov_left = self._provinces_left(state)
        smithies = self._count(player, "Smithy")

        # 1) Provinces always when affordable.
        if coins >= 8 and "Province" in card:
            return card["Province"]

        # 2) Endgame VP rules (pressure matters in BM mirrors).
        if prov_left <= 4:
            # Prefer Duchy on $5+ over more economy once the pile is low.
            if coins >= 5 and "Duchy" in card:
                return card["Duchy"]
        if prov_left <= 2:
            if coins >= 2 and "Estate" in card:
                return card["Estate"]

        # 3) Payload
        if coins >= 6 and "Gold" in card:
            return card["Gold"]

        # 4) Smithy buys (tempo-limited, early only).
        #    Buy at exactly $4, cap at 2 copies, and avoid when Provinces already low.
        if coins == 4 and smithies < 2 and prov_left > 6 and "Smithy" in card:
            return card["Smithy"]

        # 5) Silver fallback (solid in BM, especially when we miss $6).
        if coins >= 3 and "Silver" in card:
            # Minor tweak: if coins == 5 and Duchy rule didn't trigger (prov_left > 4), prefer Silver.
            return card["Silver"]

        # Nothing worthwhile
        return None


def create_big_money_smithy() -> EnhancedStrategy:
    return BigMoneySmithyStrategy()
