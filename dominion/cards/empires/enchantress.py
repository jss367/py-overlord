"""Enchantress: $3 Action-Attack-Duration.

Until your next turn, the first time each other player plays an Action card
on their turn, they get +1 Card +1 Action instead of following its
instructions. At the start of your next turn, +2 Cards.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Enchantress(Card):
    def __init__(self):
        super().__init__(
            name="Enchantress",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack(target):
            target.enchantress_active = True

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack, attacker=player, attack_card=self)

        if self not in player.duration:
            player.duration.append(self)
        # Move from in_play if it ended up there too (Throne Room flows etc.)
        if self in player.in_play:
            player.in_play.remove(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        # Start of caster's next turn: +2 Cards, clear flags.
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        for other in game_state.players:
            if other is player:
                # Clear our own flag too just in case.
                other.enchantress_active = False
                other.enchantress_used_this_turn = False
            else:
                other.enchantress_active = False
                other.enchantress_used_this_turn = False
        # Allow this card to leave duration after this trigger.
        self.duration_persistent = False
