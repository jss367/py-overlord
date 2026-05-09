"""Scrying Pool - Action - Attack from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class ScryingPool(Card):
    """Action - Attack ($2P): +1 Action.

    Each player (including you) reveals the top card of their deck and
    either discards it or puts it back, your choice. Then reveal cards from
    the top of your deck until revealing one that isn't an Action. Put all
    of those revealed cards into your hand.
    """

    def __init__(self):
        super().__init__(
            name="Scrying Pool",
            cost=CardCost(coins=2, potions=1),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        attacker = game_state.current_player

        # Self-target first (no reaction window for self).
        self._reveal_and_choose(game_state, attacker, attacker, is_self=True)

        for other in game_state.players:
            if other is attacker:
                continue

            def attack_target(target, _attacker=attacker):
                self._reveal_and_choose(
                    game_state, _attacker, target, is_self=False
                )

            game_state.attack_player(
                other, attack_target, attacker=attacker, attack_card=self
            )

        # Then: reveal cards from top of attacker's deck until a non-Action,
        # putting all revealed cards into hand.
        revealed: list = []
        while True:
            if not attacker.deck and attacker.discard:
                attacker.shuffle_discard_into_deck()
            if not attacker.deck:
                break
            card = attacker.deck.pop()
            revealed.append(card)
            if not card.is_action:
                break
        if revealed:
            attacker.hand.extend(revealed)

    @staticmethod
    def _reveal_and_choose(game_state, attacker, target, is_self: bool):
        if not target.deck and target.discard:
            target.shuffle_discard_into_deck()
        if not target.deck:
            return
        revealed = target.deck.pop()
        discard = attacker.ai.choose_topdeck_or_discard(
            game_state, attacker, target, revealed, is_self=is_self
        )
        if discard:
            game_state.discard_card(target, revealed)
        else:
            target.deck.append(revealed)
