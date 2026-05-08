from ..base_card import Card, CardCost, CardStats, CardType


class Footpad(Card):
    """+2 Coffers. Each other player discards down to 3 cards in hand.
    When another player gains a Victory card, you may reveal this from
    your hand for +1 Card."""

    def __init__(self):
        super().__init__(
            name="Footpad",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.coin_tokens += 2

        def attack_target(target):
            if len(target.hand) <= 3:
                return
            discard_needed = len(target.hand) - 3
            selected = target.ai.choose_cards_to_discard(
                game_state, target, list(target.hand), discard_needed, reason="footpad"
            )
            for card in selected[:discard_needed]:
                if card in target.hand:
                    target.hand.remove(card)
                    game_state.discard_card(target, card)
            while len(target.hand) > 3:
                # Defensive: ensure attack always reduces to 3.
                card = target.hand[0]
                target.hand.remove(card)
                game_state.discard_card(target, card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(
                other, attack_target, attacker=player, attack_card=self
            )

    def on_opponent_gain(self, game_state, player, gainer, gained_card) -> None:
        """Hand reaction: when an opponent gains a Victory card, reveal this
        for +1 Card. ``player`` is the Footpad owner, ``gainer`` is the
        other player who just gained."""
        if not gained_card.is_victory:
            return
        if self not in player.hand:
            return
        decision = getattr(player.ai, "should_react_with_footpad", None)
        if decision is None or not decision(game_state, player, gainer, gained_card):
            return
        # Reveal (do not move). +1 Card.
        game_state.draw_cards(player, 1)
