from .base_ally import Ally


class CircleOfWitches(Ally):
    """After you play an Attack, you may spend 3 Favors to make each
    opponent gain a Curse.
    """

    def __init__(self):
        super().__init__("Circle of Witches")

    def on_play_card(self, game_state, player, card) -> None:
        from dominion.cards.registry import get_card

        if not card.is_attack:
            return
        if player.favors < 3:
            return
        if game_state.supply.get("Curse", 0) <= 0:
            return
        player.favors -= 3
        for opponent in game_state.players:
            if opponent is player:
                continue

            def attack(target):
                if game_state.supply.get("Curse", 0) <= 0:
                    return
                game_state.supply["Curse"] -= 1
                game_state.gain_card(target, get_card("Curse"))

            game_state.attack_player(opponent, attack)
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                "spends 3 Favors on Circle of Witches: each opponent gains a Curse",
                {"favors_remaining": player.favors},
            )
        )
