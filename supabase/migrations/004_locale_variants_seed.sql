-- Ensure locale variants exist for training FK constraints and LLM shorthand values.

insert into locale_variants(id, country, region, label, default_formality, pronoun_policy, notes)
values
(
  'es-UY-montevideo',
  'Uruguay',
  'Montevideo',
  'Uruguayan Spanish / Montevideo',
  'polite_neutral',
  'vos default where natural; ustedes plural',
  'MVP default locale.'
),
(
  'es-UY',
  'Uruguay',
  null,
  'Uruguayan Spanish',
  'polite_neutral',
  'vos default where natural',
  'LLM shorthand alias'
)
on conflict (id) do nothing;
