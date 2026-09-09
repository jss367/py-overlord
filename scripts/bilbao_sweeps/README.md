# Bilbao hand-search sweep inputs

Variant definitions used by `scripts/bilbao_variants.py` for the Bilbao board
guide (`reports/strategies/bilbao-strategy-guide.html`). Each file maps a
variant name to keyword arguments of `BilbaoAnvilFeodumVariant`
(`dominion/strategy/strategies/bilbao_seeds.py`); an empty object is the
round-robin leader unchanged. Run from the repository root:

```
PYTHONPATH=. python scripts/bilbao_variants.py --sweep scripts/bilbao_sweeps/sweep1.json --champion base --games 200
PYTHONPATH=. python scripts/bilbao_variants.py --sweep scripts/bilbao_sweeps/sweep2.json --games 100 --extra "Bilbao Fools Gold Rush" "Bilbao Sheepdog Anvil Money"
PYTHONPATH=. python scripts/bilbao_variants.py --sweep scripts/bilbao_sweeps/sweep3.json --games 100
PYTHONPATH=. python scripts/bilbao_variants.py --sweep scripts/bilbao_sweeps/sweep4a.json --games 400
PYTHONPATH=. python scripts/bilbao_variants.py --sweep scripts/bilbao_sweeps/sweep4b.json --champion b8 --games 200
PYTHONPATH=. python scripts/bilbao_variants.py --sweep scripts/bilbao_sweeps/sweep5.json --champion e4_feo3_duchy6 --games 400
PYTHONPATH=. python scripts/bilbao_variants.py --sweep scripts/bilbao_sweeps/sweep6_raider.json --champion best --games 400
```

`sweep6_raider.json` re-measures one and two Raiders on the published chassis
after Raider was corrected to a Night card; the Raider Money seed re-check is
`PYTHONPATH=. python scripts/search_bilbao.py --games 400 --champion "Bilbao Best Found" --strategies "Bilbao Raider Money" BigMoney`.

`sweep3.json` omits the never-buy-Province variant (`province_min: 99`) that was
dropped mid-run after losing about 95% of its games.
