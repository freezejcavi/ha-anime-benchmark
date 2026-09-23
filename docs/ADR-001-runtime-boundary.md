# ADR-001: Supabase mimo runtime scorer

## Decision

Produkční benchmark v Home Assistant nebude při výpočtu kontaktovat Supabase.

## Reason

- menší latence
- žádné zatěžování tracker DB
- scorer funguje i při výpadku Supabase
- model je verzovatelný a testovatelný jako immutable bundle
- změna modelu se publikuje explicitně, ne skrytě za běhu

## Consequence

Je nutný explicitní export/sync `model_bundle.json`. Integrace odmítne načíst nekompletní bundle. Každá změna produkčního affinity modelu musí aktualizovat bundle a projít CI validací.
