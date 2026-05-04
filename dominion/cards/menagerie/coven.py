"""Coven - Action-Attack from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Coven(Card):
    """+1 Action +$2. Each other player exiles a Curse from the Supply or, if
    not, gains a Curse from the trash if any.
    """

    def __init__(self):
        super().__init__(
            name="Coven",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        for other in game_state.players:
            if other is player:
                continue

            def attack_target(target):
                if game_state.supply.get("Curse", 0) > 0:
                    game_state.supply["Curse"] -= 1
                    target.exile.append(get_card("Curse"))
                    return
                # Otherwise: gain a Curse from trash if any
                trashed = next(
                    (c for c in game_state.trash if c.name == "Curse"), None
                )
                if trashed:
                    game_state.trash.remove(trashed)
                    game_state.gain_card(target, trashed, from_supply=False)

            game_state.attack_player(
                other, attack_target, attacker=player, attack_card=self
            )
