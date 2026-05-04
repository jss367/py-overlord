"""Cultist — $5 Action-Attack-Looter that hands out Ruins and chains itself."""

from ..base_card import Card, CardCost, CardStats, CardType


class Cultist(Card):
    """+2 Cards. Each other player gains a Ruins. You may play a Cultist from
    your hand.

    When you trash this, +3 Cards.
    """

    def __init__(self):
        super().__init__(
            name="Cultist",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.ATTACK, CardType.LOOTER],
        )

    def get_additional_piles(self) -> dict[str, int]:
        return {"Ruins": 10}

    def play_effect(self, game_state):
        player = game_state.current_player

        # Each other player gains a Ruins
        def attack_target(target):
            game_state.gain_ruins(target)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

        # May play another Cultist from hand
        next_cultist = next(
            (c for c in player.hand if c.name == "Cultist"), None
        )
        if next_cultist and player.ai.should_play_cultist_chain(game_state, player):
            player.hand.remove(next_cultist)
            player.in_play.append(next_cultist)
            next_cultist.on_play(game_state)
            game_state.fire_ally_play_hooks(player, next_cultist)

    def on_trash(self, game_state, player):
        game_state.draw_cards(player, 3)
