-- Produces one JSON document for custom_components/anime_benchmark/model_bundle.json.
-- Run against the canonical tracker DB after any affinity-model change.
WITH active_model AS (
  SELECT profile_id, model_version, component_weights, baseline_median_raw_fit
  FROM tracker.profile_affinity_model
  WHERE is_active = true
  LIMIT 1
),
priors AS (
  SELECT key AS component,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY value::numeric) AS component_prior
  FROM tracker.profile_content_affinity pca
  JOIN active_model am USING (profile_id, model_version)
  CROSS JOIN LATERAL jsonb_each_text(pca.component_scores)
  WHERE value <> 'null'
  GROUP BY key
),
franchise_median AS (
  SELECT percentile_cont(0.5) WITHIN GROUP (
           ORDER BY (base_affinity_index + personal_adjustment)::double precision
         ) AS pre_rating_median
  FROM reporting.v_ui_affinity_by_franchise v
  JOIN active_model am USING (profile_id)
),
rules AS (
  SELECT jsonb_agg(
    jsonb_build_object(
      'rule_id', r.rule_id,
      'component', r.component,
      'namespace', r.namespace,
      'term_pattern', r.term_pattern,
      'match_mode', r.match_mode,
      'fit_score', r.fit_score,
      'rule_weight', r.rule_weight,
      'evidence_strength', COALESCE(r.evidence_strength, 1)
    ) ORDER BY r.component, r.namespace, r.term_pattern, r.rule_id
  ) AS payload,
  count(*) AS rule_count
  FROM tracker.profile_affinity_rule r
  JOIN active_model am USING (profile_id, model_version)
)
SELECT jsonb_pretty(jsonb_build_object(
  'schema_version', 1,
  'bundle_kind', 'production-export',
  'rules_complete', true,
  'generated_at', statement_timestamp(),
  'model_version', am.model_version,
  'taxonomy_mapping_version', 'anilist-map-v0.2',
  'component_weights', am.component_weights,
  'component_priors', (SELECT jsonb_object_agg(component, component_prior) FROM priors),
  'baseline_median_raw_fit', am.baseline_median_raw_fit,
  'franchise_pre_rating_median', (SELECT pre_rating_median FROM franchise_median),
  'display', jsonb_build_object('minimum', 1.0, 'slope', 7.0, 'anchor', 0.817163, 'round_digits', 2),
  'rule_count', rules.rule_count,
  'rules', rules.payload
)) AS model_bundle
FROM active_model am CROSS JOIN rules;
