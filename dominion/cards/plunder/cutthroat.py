"""Cutthroat from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Cutthroat(Card):
    """$5 Action-Attack: +$2. Each other player discards down to 3 cards.
    The next time anyone gains a Loot this turn, you also gain a Loot.
    """

    def __init__(self):
        super().__init__(
            name="Cutthroat",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )
        self._owner = None
        self._loot_reaction_armed = False

    def play_effect(self, game_state):
        player = game_state.current_player
        self._owner = player
        self._loot_reaction_armed = True

        def discard_to_three(target):
            if len(target.hand) <= 3:
                return

            discard_count = len(target.hand) - 3
            choices = list(target.hand)
            selected = target.ai.choose_cards_to_discard(
                game_state,
                target,
                choices,
                discard_count,
                reason="cutthroat",
            )

            remaining = list(choices)
            picked = []
            for card in selected:
                if card in remaining:
                    remaining.remove(card)
                    picked.append(card)

            while len(picked) < discard_count and remaining:
                picked.append(remaining.pop(0))

            for card in picked:
                if card in target.hand:
                    target.hand.remove(card)
                    game_state.discard_card(target, card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, discard_to_three)

    def on_card_gained(self, game_state, owner, gainer, gained_card):
        from .loot_cards import LOOT_CARD_NAMES
        from ..registry import get_card

        if not self._loot_reaction_armed:
            return
        if owner is not self._owner:
            return
        if gained_card.name not in LOOT_CARD_NAMES:
            return

        self._loot_reaction_armed = False

        import random

        loot_name = random.choice(LOOT_CARD_NAMES)
        loot = get_card(loot_name)
        game_state.gain_card(owner, loot)

    def on_discard_from_play(self, game_state, player):
        self._loot_reaction_armed = False
        self._owner = None
