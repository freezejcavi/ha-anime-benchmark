-- Export the local anime/donghua franchise index used by Anime Benchmark.
-- Supabase is not queried by the Home Assistant runtime.
select jsonb_pretty(jsonb_build_object(
  'schema_version', 1,
  'generated_at', statement_timestamp(),
  'items', jsonb_agg(
    jsonb_build_object(
      'franchise_id', f.franchise_id,
      'canonical_title', f.canonical_title,
      'aliases', f.aliases
    )
    order by f.canonical_title
  )
)) as catalog_index
from tracker.franchise f
where exists (
  select 1
  from tracker.content c
  where c.franchise_id=f.franchise_id
    and c.medium='animation'
    and c.animation_origin in ('anime','donghua')
);
