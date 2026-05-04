from .base_ally import Ally


class CraftersGuild(Ally):
    """At start of turn, spend 2 Favors to gain a card costing up to $4
    to your hand.
    """

    def __init__(self):
        super().__init__("Crafters' Guild")

    def on_turn_start(self, game_state, player) -> None:
        from dominion.cards.registry import get_card

        if player.favors < 2:
            return
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.potions > 0 or card.cost.coins > 4:
                continue
            if card.name == "Curse":
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)
        if not candidates:
            return
        # Skip junk-only situations.
        meaningful = [
            c for c in candidates
            if c.is_action or c.is_treasure or (c.is_victory and c.cost.coins >= 4)
        ]
        if not meaningful:
            return
        choice = max(meaningful, key=lambda c: (c.cost.coins, c.is_action, c.name))
        if game_state.supply.get(choice.name, 0) <= 0:
            return
        player.favors -= 2
        game_state.supply[choice.name] -= 1
        gained = game_state.gain_card(player, choice)
        # Move the gained card to hand.
        if gained in player.discard:
            player.discard.remove(gained)
            player.hand.append(gained)
        elif gained in player.deck:
            player.deck.remove(gained)
            player.hand.append(gained)
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"spends 2 Favors on Crafters' Guild to gain {choice} to hand",
                {"favors_remaining": player.favors},
            )
        )
