"""Amulet (Adventures) — $3 Action-Duration."""

from ..base_card import Card, CardCost, CardStats, CardType


class Amulet(Card):
    def __init__(self):
        super().__init__(
            name="Amulet",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def _resolve_choice(self, game_state, player):
        from ..registry import get_card

        options = ["coin"]
        if player.hand:
            options.append("trash")
        if game_state.supply.get("Silver", 0) > 0:
            options.append("silver")
        mode = player.ai.choose_amulet_mode(game_state, player, options)
        if mode == "coin":
            player.coins += 1
        elif mode == "trash" and player.hand:
            target = player.ai.choose_card_to_trash(game_state, list(player.hand) + [None])
            if target and target in player.hand:
                player.hand.remove(target)
                game_state.trash_card(player, target)
        elif mode == "silver" and game_state.supply.get("Silver", 0) > 0:
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))

    def play_effect(self, game_state):
        player = game_state.current_player
        self._resolve_choice(game_state, player)
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        self._resolve_choice(game_state, player)
        self.duration_persistent = False
