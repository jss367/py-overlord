"""Raider — $6 Action-Attack-Duration.

Each other player reveals their hand and discards a card you have in play
(of their choice). At the start of your next turn, +$3.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Raider(Card):
    def __init__(self):
        super().__init__(
            name="Raider",
            cost=CardCost(coins=6),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        in_play_names = {c.name for c in player.in_play}
        for other in game_state.players:
            if other is player:
                continue

            def attack(target):
                # Target reveals their hand and discards a card matching the
                # names in attacker's play (attacker chooses if multiple, but
                # we let the target's AI pick from the matches). Per Dominion
                # rules, the rest of the attack (revealing the hand and the
                # forced discard) applies regardless of hand size; hand-size
                # immunity (5+) only applies to the *initial* reveal step in
                # Pirate Ship-style attacks, not to Raider.
                matches = [c for c in target.hand if c.name in in_play_names]
                if not matches:
                    return
                chosen = target.ai.choose_card_to_discard_with_raider(
                    game_state, target, matches
                )
                if chosen is None or chosen not in target.hand:
                    chosen = matches[0]
                target.hand.remove(chosen)
                game_state.discard_card(target, chosen)

            game_state.attack_player(other, attack, attacker=player, attack_card=self)

        if self in player.in_play:
            player.in_play.remove(self)
        if self not in player.duration:
            player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 3
        self.duration_persistent = False
