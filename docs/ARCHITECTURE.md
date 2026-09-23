# Architecture

## Runtime

`Dashboard card -> HA entities -> AniList client -> taxonomy mapper -> local scorer -> sensor`

Supabase není součást runtime cesty. AniList se dotazuje pouze po explicitním stisku **Vyhodnotit**.

## Model distribution

`Supabase -> export_model_bundle.sql -> model_bundle.json -> GitHub -> HA integration`

Bundle nese:
- model version
- component weights
- complete profile affinity rules
- component priors
- main-content raw-fit median
- franchise pre-rating median
- dashboard display transform
- taxonomy mapping version
- generated timestamp + rule count

## Scoring invariant

Lokální scorer kopíruje `tracker.refresh_profile_affinity_v14`:

1. pro jeden component + namespace + term ponechá nejsilnější matching rule,
2. v každé komponentě seřadí hits stejně jako SQL a vezme top 3,
3. component score = `0.75 * max(fit) + 0.25 * weighted_mean(top3)`,
4. chybějící komponenta použije exportovaný population prior,
5. raw fit se normalizuje produkčním main-content medianem,
6. pre-watch franchise affinity nemá completion ani user-rating bonus,
7. výsledek se normalizuje franchise medianem a projde dashboard display transformací.

## AniList evidence

Genres se mapují deterministicky. Nejvýznamnější AniList tags mají explicitní aliasy do project taxonomy. Ostatní non-spoiler tags s rank >= 60 se předají jako slabší `project.subgenre` evidence; pokud žádné produkční pravidlo neodpovídá, nemají na výsledek žádný vliv.

To dovoluje využít existující regex rules bez vytváření paralelního scoring modelu.

## Design rules

- Žádný rating z neúplného bundle.
- Žádné IMDb/AniList community score ve výpočtu.
- AniList `siteUrl` slouží pouze jako detailní hyperlink.
- Cover + rok/formát slouží jako rychlá kontrola správně nalezeného titulu.
- Chybějící komponenta používá stejný population prior jako produkční model.
- Runtime benchmark nesmí zapisovat do tracker DB.
