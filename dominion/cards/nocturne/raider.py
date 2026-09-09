"""Raider — $6 Night-Duration-Attack.

Played in the Night phase, after Treasures, so "a card you have in play"
includes every Treasure played this turn. Each other player with 5 or more
cards in hand discards a copy of a card you have in play (or reveals they
can't). At the start of your next turn, +$3.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Raider(Card):
    def __init__(self):
        super().__init__(
            name="Raider",
            cost=CardCost(coins=6),
            stats=CardStats(),
            types=[CardType.NIGHT, CardType.DURATION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        in_play_names = {c.name for c in player.in_play}
        for other in game_state.players:
            if other is player:
                continue

            def attack(target):
                # Card text: "Each other player with 5 or more cards in hand
                # discards a copy of a card you have in play (or reveals they
                # can't)." Targets holding 4 or fewer cards are unaffected.
                if len(target.hand) < 5:
                    return
                # The target chooses which matching card to discard.
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
