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


## v0.3 catalog awareness

The integration ships a read-only local tracker catalog exported from the canonical Supabase tracker.

For each AniList candidate/result the card displays:

- **TRACKED** — conservative canonical/alias franchise match exists in the tracker.
- **NEW** — no local tracker match was found.

The current fallback is intentionally conservative: exact normalized title match first, then a guarded franchise-prefix match. It does not write to the tracker.

The frontend resource URL remains:

`/api/anime_benchmark/static/anime-benchmark-card.js`

From v0.3 this file is a stable loader. It imports the actual card implementation with a cache-busting query string on each page load. After the one-time transition to v0.3, normal browser reloads should pick up future card changes without manual resource URL versioning.

The card itself displays its UI version in the **Aktivita** footer, making backend/frontend version mismatches visible.


## Automatic Lovelace resource versioning (v0.3.2+)

The integration now manages its own Lovelace card resource when Lovelace resources use storage mode. On startup it:

1. Finds existing Anime Benchmark resources.
2. Updates the primary resource to the direct implementation URL with the installed integration version as a cache-busting query parameter.
3. Removes stale duplicate Anime Benchmark resource entries.

Example:

`/api/anime_benchmark/static/anime-benchmark-card.impl.js?v=0.3.2`

This removes the need to manually edit the resource URL after normal HACS updates.


## Release marker

Releases are triggered only when `.release-version` is updated to match the manifest version. This marker is intentionally committed last so the generated GitHub tag always contains the complete version payload.


## One-click Later importer

From v0.4 the final **NEW** benchmark result can be submitted directly to the canonical tracker as **Later**.

Runtime flow:

`NEW result -> + Later -> GitHub transaction -> tracker PROD writer -> Supabase`

The Home Assistant integration never receives a database credential and never writes to Supabase directly. It creates one immutable transaction file in `freezejcavi/anime-series-tracker`. The existing tracker GitHub Actions writer validates the transaction, applies it atomically, runs the continuity gate, and records it in the transaction ledger.

### One-time GitHub setup

Create a fine-grained GitHub personal access token limited to:

- Repository: `freezejcavi/anime-series-tracker`
- Repository permission: **Contents: Read and write**

No database credential is stored in Home Assistant.

Then open:

`Settings -> Devices & services -> Anime Benchmark -> Configure`

and paste the token. Leave the defaults unless the tracker repository/profile changes:

- repository: `freezejcavi/anime-series-tracker`
- branch: `main`
- profile: `pr_4a017461bfff446d`

A blank token field on a later Configure visit keeps the already stored token.

### Safety behavior

- The card exposes **+ Later** only for a final result classified as **NEW**.
- The backend re-fetches the AniList record by ID before submission; metadata is not trusted from browser JS.
- The transaction carries AniList ID, verified metadata, mapped taxonomy and benchmark audit values.
- The tracker importer checks AniList ID first and is duplicate-safe.
- Ambiguous franchise matches fail instead of guessing.
- Existing watched/active state is never silently overwritten.
- The card says **Odesláno importeru** after the GitHub transaction is accepted. This means submitted to the automatic importer, not a claim that the database workflow has already completed.


## Live tracker status overlay (v0.4.1+)

The bundled `catalog_index.json` remains the fast offline baseline for TRACKED/NEW detection.

For titles that are not present in that snapshot, the Lovelace card additionally reads the existing Home Assistant entity:

`sensor.anime_tracker_home_feed`

and checks its live queue attributes:

- `active_items`
- `later_items`
- `waiting_dub_items`
- `waiting_release_items`

The card does not add a polling timer or another database/GitHub request. Home Assistant already pushes updated state objects to the card whenever the tracker feed changes. A newly imported title therefore changes from **NEW** to **TRACKED** on the next normal tracker-feed update.

If the tracker feed entity is unavailable, the card simply falls back to the bundled catalog snapshot.
