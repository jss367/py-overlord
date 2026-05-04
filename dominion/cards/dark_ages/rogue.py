"""Rogue — $5 Action-Attack that trashes from deck-tops or gains from trash."""

from ..base_card import Card, CardCost, CardStats, CardType


class Rogue(Card):
    """+$2. Each other player reveals the top 2 cards of their deck. If any
    cost between $3 and $6, you choose one to trash; otherwise they discard.

    If there are any cards in the trash costing $3 to $6, gain one (this
    happens before the attacks).
    """

    def __init__(self):
        super().__init__(
            name="Rogue",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        attacker = game_state.current_player

        # If there are any $3-$6 cards in the trash, gain one (per official
        # text the trash check happens after attacks; we run it after as well
        # to satisfy the "if any" wording).

        def attack_target(target):
            revealed: list[Card] = []
            for _ in range(2):
                if not target.deck and target.discard:
                    target.shuffle_discard_into_deck()
                if not target.deck:
                    break
                revealed.append(target.deck.pop())

            if not revealed:
                return

            game_state.log_callback(
                (
                    "action",
                    target.ai.name,
                    f"reveals top of deck for Rogue: {[c.name for c in revealed]}",
                    {"revealed": [c.name for c in revealed]},
                )
            )

            trashable = [c for c in revealed if 3 <= c.cost.coins <= 6]

            if trashable:
                if len(trashable) == 1:
                    chosen = trashable[0]
                else:
                    chosen = attacker.ai.choose_knight_to_trash(
                        game_state, attacker, target, list(trashable)
                    )
                    if chosen not in trashable:
                        chosen = max(
                            trashable, key=lambda c: (c.cost.coins, c.name)
                        )
                revealed.remove(chosen)
                game_state.trash_card(target, chosen)
                # Discard the rest
                for card in revealed:
                    game_state.discard_card(target, card)
            else:
                # Discard everything if nothing was eligible
                for card in revealed:
                    game_state.discard_card(target, card)

        for other in game_state.players:
            if other is attacker:
                continue
            game_state.attack_player(other, attack_target)

        # Now check trash for $3-$6 to gain
        eligible_in_trash = [
            c for c in game_state.trash if 3 <= c.cost.coins <= 6
        ]
        if eligible_in_trash:
            choice = attacker.ai.should_gain_from_trash_with_rogue(
                game_state, attacker, list(eligible_in_trash)
            )
            if choice and choice in game_state.trash:
                game_state.trash.remove(choice)
                # Gain from trash; do not touch supply.
                game_state.gain_card(attacker, choice, from_supply=False)
