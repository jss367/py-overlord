"""Implementation of the Spy (1E) attack card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Spy(Card):
    """Action - Attack ($4): +1 Card, +1 Action.

    Each player (including you) reveals the top card of their deck and
    either discards it or puts it back, your choice.
    """

    def __init__(self):
        super().__init__(
            name="Spy",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        attacker = game_state.current_player

        # The Spy player isn't attacked by their own Spy — Moat etc. only
        # apply to "other" players. But the rule still has us reveal our own
        # top card. We process the attacker first without going through
        # attack_player (no reaction window for self).
        self._spy_self(game_state, attacker)

        for other in game_state.players:
            if other is attacker:
                continue

            def attack_target(target, _attacker=attacker):
                self._spy_other(game_state, _attacker, target)

            game_state.attack_player(other, attack_target)

    @staticmethod
    def _reveal_top(player):
        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return None
        return player.deck.pop()

    def _spy_self(self, game_state, attacker):
        revealed = self._reveal_top(attacker)
        if revealed is None:
            return
        # Attacker chooses for themselves. Default heuristic: discard junk,
        # otherwise topdeck.
        discard = attacker.ai.choose_topdeck_or_discard(
            game_state, attacker, attacker, revealed, is_self=True
        )
        if discard:
            game_state.discard_card(attacker, revealed)
            game_state.log_callback(
                (
                    "action",
                    attacker.ai.name,
                    f"discards own {revealed} via Spy",
                    {"revealed": revealed.name},
                )
            )
        else:
            attacker.deck.append(revealed)
            game_state.log_callback(
                (
                    "action",
                    attacker.ai.name,
                    f"keeps own {revealed} on top via Spy",
                    {"revealed": revealed.name},
                )
            )

    def _spy_other(self, game_state, attacker, target):
        revealed = self._reveal_top(target)
        if revealed is None:
            return
        # Attacker chooses what the target does. Default: discard good cards,
        # keep junk on top.
        discard = attacker.ai.choose_topdeck_or_discard(
            game_state, attacker, target, revealed, is_self=False
        )
        if discard:
            game_state.discard_card(target, revealed)
            game_state.log_callback(
                (
                    "action",
                    target.ai.name,
                    f"discards {revealed} due to Spy",
                    {"revealed": revealed.name},
                )
            )
        else:
            target.deck.append(revealed)
            game_state.log_callback(
                (
                    "action",
                    target.ai.name,
                    f"keeps {revealed} on top due to Spy",
                    {"revealed": revealed.name},
                )
            )
