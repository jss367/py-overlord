from .base_ally import Ally


class WoodworkersGuild(Ally):
    """At start of turn, may spend 1 Favor: trash an Action from hand
    and gain an Action.
    """

    def __init__(self):
        super().__init__("Woodworkers' Guild")

    def on_turn_start(self, game_state, player) -> None:
        from dominion.cards.registry import get_card

        if player.favors <= 0:
            return
        actions_in_hand = [c for c in player.hand if c.is_action]
        if not actions_in_hand:
            return
        # Trash the cheapest Action; gain an Action of equal or higher
        # cost up to ``cost + 2``.
        target = min(actions_in_hand, key=lambda c: (c.cost.coins, c.name))
        max_cost = target.cost.coins + 2
        candidates: list = []
        for name, count in game_state.supply.items():
            if count <= 0 or name == target.name:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action:
                continue
            if card.cost.potions > 0 or card.cost.coins > max_cost:
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)
        if not candidates:
            return
        choice = max(candidates, key=lambda c: (c.cost.coins, c.name))
        if game_state.supply.get(choice.name, 0) <= 0:
            return
        player.favors -= 1
        if target in player.hand:
            player.hand.remove(target)
            game_state.trash_card(player, target)
        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice)
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"spends a Favor on Woodworkers' Guild (trash {target}, gain {choice})",
                {"favors_remaining": player.favors},
            )
        )
