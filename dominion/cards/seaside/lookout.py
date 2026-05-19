"""Implementation of the Lookout sifter."""

from ..base_card import Card, CardCost, CardStats, CardType


class Lookout(Card):
    _STARTER_JUNK_NAMES = {"Copper", "Estate", "Hovel", "Overgrown Estate"}

    def __init__(self):
        super().__init__(
            name="Lookout",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed = []

        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        trash_card = min(revealed, key=self._trash_priority)
        revealed.remove(trash_card)
        game_state.trash_card(player, trash_card)

        if revealed:
            discard_card = min(revealed, key=self._discard_priority)
            revealed.remove(discard_card)
            game_state.discard_card(player, discard_card)

        if revealed:
            player.deck.append(revealed[0])

    @staticmethod
    def _trash_priority(card):
        if card.name == "Curse":
            return (0, card.cost.coins, card.name)
        if card.is_ruins:
            return (1, card.cost.coins, card.name)
        if card.name in Lookout._STARTER_JUNK_NAMES:
            return (2, Lookout._card_strength(card))
        return (3, Lookout._card_strength(card))

    @staticmethod
    def _discard_priority(card):
        return Lookout._card_strength(card)

    @staticmethod
    def _card_strength(card):
        """Rank cards from weakest to strongest for Lookout's default choices."""
        if card.name == "Curse":
            return (0, card.cost.coins, card.name)
        if card.is_ruins:
            return (
                1,
                card.stats.cards,
                card.stats.actions,
                card.stats.coins,
                card.stats.buys,
                card.cost.coins,
                card.name,
            )
        if card.name in Lookout._STARTER_JUNK_NAMES:
            return (
                2,
                card.stats.coins,
                card.stats.vp,
                card.cost.coins,
                card.name,
            )
        return (
            3,
            card.cost.coins,
            card.cost.potions,
            card.cost.debt,
            card.stats.vp,
            card.stats.coins,
            card.stats.cards,
            card.stats.actions,
            card.stats.buys,
            card.name,
        )
