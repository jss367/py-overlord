from ..base_card import Card, CardCost, CardStats, CardType


class Torturer(Card):
    def __init__(self):
        super().__init__(
            name="Torturer",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        """Each other player chooses to discard two cards or gain a Curse to their hand."""

        current_player = game_state.current_player

        def discard_priority(card):
            """Lower score means the card is more expendable."""

            if card.name == "Curse":
                return 0
            if card.is_victory and card.name != "Mill":
                return 1
            if card.name == "Copper":
                return 2
            if card.is_treasure:
                return 4
            if card.cost.coins >= 5:
                return 5
            return 3

        def select_low_priority_cards(target, count):
            if count <= 0 or not target.hand:
                return []
            sorted_hand = sorted(target.hand, key=lambda c: (discard_priority(c), c.name))
            return sorted_hand[: min(count, len(sorted_hand))]

        def discard_cards(target, cards_to_discard):
            if not cards_to_discard:
                return
            for card in cards_to_discard:
                if card in target.hand:
                    target.hand.remove(card)
                target.discard.append(card)

        def gain_curse_to_hand(target):
            if game_state.supply.get("Curse", 0) <= 0:
                return False

            from ..registry import get_card

            previous_counts = {
                pile: sum(1 for c in getattr(target, pile) if c.name == "Curse")
                for pile in ("hand", "deck", "discard")
            }

            curse = get_card("Curse")
            game_state.supply["Curse"] -= 1
            game_state.gain_card(target, curse)

            gained_card = None
            for pile in ("hand", "deck", "discard"):
                pile_cards = getattr(target, pile)
                curse_cards = [c for c in pile_cards if c.name == "Curse"]
                if len(curse_cards) > previous_counts[pile]:
                    gained_card = curse_cards[-1]
                    pile_cards.remove(gained_card)
                    break

            if gained_card is None:
                return False

            target.hand.append(gained_card)

            if game_state.logger:
                target_name = game_state.logger.format_player_name(target.ai.name)
                source_name = game_state.logger.format_player_name(current_player.ai.name)
            else:
                target_name = target.ai.name
                source_name = current_player.ai.name

            game_state.log_callback(
                (
                    "action",
                    source_name,
                    f"causes {target_name} to gain a Curse to hand",
                    {"curses_remaining": game_state.supply.get("Curse", 0)},
                )
            )

            return True

        def attack_target(target):
            if len(target.hand) < 2:
                if not gain_curse_to_hand(target):
                    cards = select_low_priority_cards(target, len(target.hand))
                    discard_cards(target, cards)
                return

            preferred_discards = select_low_priority_cards(target, 2)
            curse_penalty = 3

            if len(preferred_discards) < 2:
                if not gain_curse_to_hand(target):
                    discard_cards(target, preferred_discards)
                return

            discard_score = sum(discard_priority(card) for card in preferred_discards)

            if discard_score > curse_penalty and gain_curse_to_hand(target):
                return

            discard_cards(target, preferred_discards)

            if game_state.logger:
                target_name = game_state.logger.format_player_name(target.ai.name)
                source_name = game_state.logger.format_player_name(current_player.ai.name)
            else:
                target_name = target.ai.name
                source_name = current_player.ai.name

            game_state.log_callback(
                (
                    "action",
                    source_name,
                    f"forces {target_name} to discard 2 cards",
                    {
                        "discarded": [card.name for card in preferred_discards],
                        "hand_size": len(target.hand),
                    },
                )
            )

        for player in game_state.players:
            if player is current_player:
                continue
            game_state.attack_player(player, attack_target)
