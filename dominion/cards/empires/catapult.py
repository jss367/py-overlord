from ..base_card import CardCost, CardStats, CardType
from ..split_pile import TopSplitPileCard


class Catapult(TopSplitPileCard):
    """Catapult: trash a card for coins and conditional attacks."""

    partner_card_name = "Rocks"

    def __init__(self):
        super().__init__(
            name="Catapult",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        to_trash = player.ai.choose_card_to_trash(
            game_state, list(player.hand) + [None]
        )
        if to_trash is None:
            return
        if to_trash not in player.hand:
            return

        get_cost = getattr(game_state, "get_card_cost", None)
        trashed_cost = (
            get_cost(player, to_trash) if get_cost is not None else to_trash.cost.coins
        )
        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)
        player.coins += min(2, trashed_cost)

        gives_curse = trashed_cost >= 3
        discards_to_three = to_trash.is_treasure
        if not gives_curse and not discards_to_three:
            return

        def attack(target):
            if gives_curse:
                game_state.give_curse_to_player(target)

            excess = len(target.hand) - 3
            if discards_to_three and excess > 0:
                choices = target.ai.choose_cards_to_discard(
                    game_state, target, list(target.hand), excess, reason="catapult"
                )
                chosen = []
                for card in choices or []:
                    if (
                        card in target.hand
                        and card not in chosen
                        and len(chosen) < excess
                    ):
                        chosen.append(card)
                if len(chosen) < excess:
                    for card in list(target.hand):
                        if card not in chosen:
                            chosen.append(card)
                        if len(chosen) == excess:
                            break
                for card in chosen:
                    if card in target.hand:
                        target.hand.remove(card)
                        game_state.discard_card(target, card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack, attacker=player, attack_card=self)
