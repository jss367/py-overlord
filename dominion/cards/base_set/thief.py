"""Implementation of the Thief (1E) attack card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Thief(Card):
    """Action - Attack ($4):

    Each other player reveals the top 2 cards of their deck. If they
    revealed any Treasures, they trash one of them that you choose. You may
    gain any or all of these trashed cards. They discard the other revealed
    cards.
    """

    def __init__(self):
        super().__init__(
            name="Thief",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        attacker = game_state.current_player
        trashed_treasures = []

        def attack_target(target, _attacker=attacker, _trashed=trashed_treasures):
            revealed = []
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
                    f"reveals top of deck for Thief: {[c.name for c in revealed]}",
                    {"revealed": [c.name for c in revealed]},
                )
            )

            treasures = [c for c in revealed if c.is_treasure]
            if treasures:
                # Attacker chooses which treasure to trash.
                if len(treasures) == 1:
                    chosen = treasures[0]
                else:
                    chosen = _attacker.ai.choose_treasure_to_trash_with_thief(
                        game_state, _attacker, target, list(treasures)
                    )
                    if chosen not in treasures:
                        chosen = max(
                            treasures,
                            key=lambda c: (c.cost.coins, c.name),
                        )
                revealed.remove(chosen)
                game_state.trash_card(target, chosen)
                _trashed.append(chosen)

            # Discard everything else revealed.
            for card in revealed:
                game_state.discard_card(target, card)

        for other in game_state.players:
            if other is attacker:
                continue
            game_state.attack_player(other, attack_target)

        # Attacker may gain any or all of the trashed Treasures.
        for card in list(trashed_treasures):
            if card not in game_state.trash:
                continue
            if not attacker.ai.should_gain_thief_treasure(game_state, attacker, card):
                continue
            game_state.trash.remove(card)
            game_state.discard_card(attacker, card)
            card.on_gain(game_state, attacker)
            game_state.log_callback(
                (
                    "action",
                    attacker.ai.name,
                    f"gains {card} from Thief's trash",
                    {"gained": card.name},
                )
            )
