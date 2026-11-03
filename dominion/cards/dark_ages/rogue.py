"""Rogue — $5 Action-Attack that trashes from deck-tops or gains from trash."""

from ..base_card import Card, CardCost, CardStats, CardType


def attack_trash_candidates(game_state, cards):
    """The shared Rogue/Knights interval excludes every Potion/Debt cost."""
    return [c for c in cards if (
        3 <= game_state.get_card_cost(game_state.turn_player, c) <= 6
        and c.cost.potions == 0 and c.cost.debt == 0
    )]


def opponents_in_order(game_state, attacker):
    start = game_state.players.index(attacker)
    return [game_state.players[(start + offset) % len(game_state.players)]
            for offset in range(1, len(game_state.players))]


class Rogue(Card):
    """+$2. Gain a $3-$6 card from the trash if possible; otherwise attack.

    Each victim reveals two cards, trashes one costing $3-$6 if possible,
    and discards the rest. Newly trashed cards are not gained by this play.
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

        eligible = attack_trash_candidates(game_state, game_state.trash)
        if eligible:
            choice = attacker.ai.should_gain_from_trash_with_rogue(
                game_state, attacker, list(eligible)
            )
            if choice not in eligible:
                from dominion.ai.tactical_defaults import rogue_gain

                choice = rogue_gain(game_state, attacker, eligible)
            game_state.trash.remove(choice)
            game_state.gain_card(attacker, choice, from_supply=False)
            return

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

            trashable = attack_trash_candidates(game_state, revealed)

            if trashable:
                if len(trashable) == 1:
                    chosen = trashable[0]
                else:
                    # "trashes one of them": the attacked player chooses.
                    chosen = target.ai.choose_card_to_trash_for_rogue_attack(
                        game_state, target, list(trashable)
                    )
                    if chosen not in trashable:
                        chosen = min(
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

        for other in opponents_in_order(game_state, attacker):
            game_state.attack_player(other, attack_target)
