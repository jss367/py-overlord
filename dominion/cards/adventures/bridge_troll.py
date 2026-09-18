"""Bridge Troll (Adventures) — $5 Action-Attack-Duration."""

from ..base_card import Card, CardCost, CardStats, CardType


class BridgeTroll(Card):
    def __init__(self):
        super().__init__(
            name="Bridge Troll",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            # "Each other player takes their -$1 token." This is the -$1
            # token, not the -1 Card token that Borrow and Relic hand out,
            # and each player owns one of it: a second Troll in the same
            # round does not stack a second penalty.
            target.take_minus_coin_token()

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target, attacker=player, attack_card=self)

        player.buys += 1
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.buys += 1
        self.duration_persistent = False
