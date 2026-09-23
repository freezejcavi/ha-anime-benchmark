# Anime Benchmark for Home Assistant

Samostatná Home Assistant custom integration pro rychlé ohodnocení anime podle osobního `profile-affinity` modelu.

## Cíl V1

1. Do dashboard karty zadat název anime.
2. Vyhledat titul přes AniList GraphQL API.
3. Převést AniList genres/tags do lokálního taxonomy vstupu.
4. Spočítat benchmark rating lokálně podle verzovaného `model_bundle.json`.
5. Zobrazit nalezený titul, cover, rating, confidence a odkaz na AniList v novém okně.

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
button_entity: button.anime_benchmark_calculate
rating_entity: sensor.anime_benchmark_rating
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
