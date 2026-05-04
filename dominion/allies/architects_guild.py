from .base_ally import Ally


class ArchitectsGuild(Ally):
    """When you gain a Victory card, you may spend 2 Favors to gain a
    cheaper card.
    """

    def __init__(self):
        super().__init__("Architects' Guild")

    def on_owner_gain(self, game_state, player, gained_card) -> None:
        from dominion.cards.registry import get_card

        if not gained_card.is_victory:
            return
        if player.favors < 2:
            return
        # Pick the most expensive non-Victory non-Curse target available
        # below the gained card's cost.
        max_cost = gained_card.cost.coins - 1
        if max_cost < 0:
            return
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.potions > 0 or card.cost.coins > max_cost:
                continue
            if card.name in {"Curse"}:
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)
        if not candidates:
            return
        # Skip if the only options are clear junk.
        meaningful = [
            c for c in candidates if not (c.is_victory and c.cost.coins <= 2)
        ]
        if not meaningful:
            return
        choice = max(meaningful, key=lambda c: (c.cost.coins, c.is_action, c.name))
        if game_state.supply.get(choice.name, 0) <= 0:
            return
        player.favors -= 2
        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice)
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"spends 2 Favors on Architects' Guild to gain {choice}",
                {"favors_remaining": player.favors},
            )
        )
