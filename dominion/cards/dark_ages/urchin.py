"""Urchin — $3 Action-Attack that may convert to Mercenary on a chained Attack."""

from ..base_card import Card, CardCost, CardStats, CardType


class Urchin(Card):
    """+1 Card +1 Action. Each other player discards down to 4 cards.

    When you play another Attack card while this is in play, you may trash
    this Urchin. If you do, gain a Mercenary.
    """

    def __init__(self):
        super().__init__(
            name="Urchin",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        attacker = game_state.current_player

        def discard_down(target):
            while len(target.hand) > 4:
                excess = len(target.hand) - 4
                chosen = target.ai.choose_cards_to_discard(
                    game_state, target, list(target.hand), excess,
                    reason="urchin",
                )
                if not chosen:
                    chosen = target.hand[:excess]
                discarded = 0
                for card in chosen:
                    if card in target.hand and discarded < excess:
                        target.hand.remove(card)
                        game_state.discard_card(target, card)
                        discarded += 1
                if discarded == 0:
                    break

        for other in game_state.players:
            if other is attacker:
                continue
            game_state.attack_player(other, discard_down)

    def react_to_attack_played(self, game_state, player, attack_card):
        """Called when player plays another Attack while this Urchin is in play.

        If the player opts in, trash this Urchin and gain a Mercenary.
        Returns True if Urchin was consumed.
        """
        from ..registry import get_card

        if attack_card is self:
            return False
        if self not in player.in_play:
            return False

        # Always trash given the Mercenary upside is strictly positive.
        player.in_play.remove(self)
        game_state.trash_card(player, self)

        if game_state.supply.get("Mercenary", 0) > 0:
            game_state.supply["Mercenary"] -= 1
            game_state.gain_card(player, get_card("Mercenary"))
        return True
