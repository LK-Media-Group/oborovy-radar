# Vlastní oborový radar

Vyberte si zdroje a časové okno. Sběrač načte RSS/Atom, odstraní opakované URL a připraví podklady. Skill z nich pomůže sestavit krátký přehled s odkazy a vysvětlením relevance. Žádný server ani napojení na týmový chat není potřeba.

## Instalace skillu

Stáhněte **Code → Download ZIP**, složku pojmenujte `oborovy-radar` a vložte ji do `.claude/skills/` ve svém projektu nebo `~/.claude/skills/`. Zachovejte celý obsah. V jiném asistentovi přiložte SKILL.md a podklady. Ukázkové zadání:

> Použijte oborovy-radar. Zajímají mě novinky pro provozovatele kurzů za poslední týden. Pracujte s těmito zdroji: [moje zdroje]. Vyberte nejvýše pět zpráv a u každé vysvětlete, proč se jí zabývat. Uveďte zdroje a co se nepodařilo ověřit.

## Vyzkoušení bez internetu

Potřebujete Python 3.10+. Spouštějte ve složce repozitáře:

```sh
mkdir -p output
python3 scripts/collect.py examples/sources.json --fixture-dir examples --from 2026-09-07T00:00:00+02:00 --until 2026-09-14T00:00:00+02:00 --output output/demo.md
```

Výsledkem jsou dvě unikátní novinky ze dvou zdrojů. Domény `.example`, organizace i obsah jsou **fiktivní**. Přepínač `--fixture-dir` zcela vypíná síť. Ukázkovou konfiguraci nepoužívejte pro živý sběr.

## Vlastní zdroje

Vytvořte `sources.local.json` se stejnou strukturou `feeds`, u každého zdroje pouze `name` a `url`. Zadejte skutečné veřejné HTTPS adresy RSS/Atom, nikoli URL běžných webových stránek. Místní konfigurace je v `.gitignore`. Pak spusťte:

```sh
python3 scripts/collect.py sources.local.json --from 2026-09-07T00:00:00+02:00 --until 2026-09-14T00:00:00+02:00 --output output/podklady.md
```

Upravte datum na požadované období. Začátek je včetně, konec bez uvedeného okamžiku. Časové pásmo je povinné. Sběrač odstraní fragmenty a běžné sledovací parametry URL; neslučuje různé adresy podle podobnosti titulků. Podklady předejte skillu, který musí přečíst a ověřit vybrané původní články. Samotný sběrač články nečte ani nehodnotí.

RSS někdy obsahuje jen posledních několik článků, mění data při aktualizaci nebo datum neuvádí. Nelze tedy slibovat úplný archiv. Položky bez použitelného data či HTTPS odkazu se přeskočí a chyba se přizná. Kód ukončení 2 znamená neúplné pokrytí, 1 chybu konfigurace, 0 dokončení bez zaznamenaných problémů. Existující výstup se nepřepisuje. Datum v názvu či ukázce není živá zpráva.

## Soukromí a hranice

Skript stahuje pouze vámi zadané veřejné feedy, bez přihlášení. Nevkládejte adresy s tajnými tokeny. Nepřistupuje ke kontaktům, poště ani ostatním souborům. Jde o místní nástroj pro vaše zdroje; nepoužívejte ho jako veřejnou službu přijímající URL od cizích lidí. Nic neplánuje a nikam nerozesílá.

```sh
python3 -m unittest discover -s tests -v
```

Testy jsou offline: RSS i Atom, duplicity, časové hranice, nedostupný zdroj, chybějící datum a odmítnutí XML entit.
