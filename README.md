# Anime Benchmark for Home Assistant

Samostatná Home Assistant custom integration pro rychlé ohodnocení anime podle osobního `profile-affinity` modelu.

## Cíl V1

1. Do dashboard karty zadat celý nebo částečný název anime.
2. Vyhledat až 5 kandidátů přes AniList GraphQL API.
3. Přesnou shodu rovnou ohodnotit; u nejasného názvu nechat uživatele vybrat správný titul.
4. Převést AniList genres/tags do lokálního taxonomy vstupu.
5. Spočítat benchmark rating lokálně podle verzovaného `model_bundle.json`.
6. Zobrazit cover, rating, confidence, AniList odkaz, stav operace a krátký activity log.

Runtime cesta **nevolá Supabase**. Supabase je pouze source-of-truth pro export model bundle.

## Runtime architektura

`Dashboard card -> HA entities -> AniList -> taxonomy mapper -> local scorer -> rating sensor`

Model bundle obsahuje produkční `profile-affinity-v1.4` váhy, priory, normalizační mediany, display transformaci a kompletní affinity rules. Osobní completion/user-rating bonusy se u benchmarku záměrně nepoužívají: jde o pre-watch odhad.

## Entity

- `text.anime_benchmark_title`
- `button.anime_benchmark_calculate`
- `sensor.anime_benchmark_rating`

## Instalace vývojové verze

1. HACS -> Custom repositories.
2. Přidej `https://github.com/freezejcavi/ha-anime-benchmark` jako **Integration**.
3. Nainstaluj Anime Benchmark a restartuj Home Assistant.
4. Settings -> Devices & services -> Add integration -> **Anime Benchmark**.
5. Přidej Lovelace resource typu JavaScript Module:
   `/api/anime_benchmark/static/anime-benchmark-card.js`

Dashboard karta:

```yaml
type: custom:anime-benchmark-card
title_entity: text.anime_benchmark_title
rating_entity: sensor.anime_benchmark_rating
height: 390
```

## Co rating znamená

Výstup používá stejnou dashboard transformaci jako tracker. Minimum je `1.00`; vyšší hodnota znamená vyšší benchmark fit vůči osobnímu affinity modelu. AniList community score, popularita ani watch time do benchmarku nevstupují.

`confidence` popisuje pokrytí modelových komponent dostupnou AniList evidencí. Pokud některá komponenta nemá dostatečnou evidenci, použije se stejný population prior jako v produkčním modelu.

## Model update

Po změně affinity modelu v canonical tracker DB spusť `tools/export_model_bundle.sql` a nahraď:

`custom_components/anime_benchmark/model_bundle.json`

Pak musí projít `tools/validate_bundle.py` a CI.

## Stav

V1 scaffold obsahuje HA backend, vlastní dashboard card, AniList resolver, lokální scorer, model export kontrakt a CI validaci. Další gate před označením verze jako stabilní je benchmark validation batch proti titulům již známým v trackeru.


## Search UX od 0.2.0

- Přesný název: titul se rovnou vyhodnotí.
- Částečný/nejasný název: karta zobrazí až 5 AniList kandidátů bez ratingu.
- Po kliknutí na **Vybrat** se spočítá rating zvoleného titulu.
- Status bar ukazuje aktuální fázi a dobu zpracování.
- Rozbalovací **Aktivita** ukazuje poslední kroky operace.
- Karta volá přímo `anime_benchmark.search`; nepoužívá závod mezi `text.set_value` a `button.press`.


## Layout

Od 0.2.2 má karta pevnou výšku (výchozí `390 px`). Kandidáti a výsledek používají vnitřní vertikální scroll pouze při přetečení. Dlouhé názvy se zobrazují maximálně na dva řádky a celý název zůstává dostupný v tooltipu. Výšku lze změnit parametrem `height` v YAML.
