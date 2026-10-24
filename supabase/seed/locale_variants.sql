-- Seed data placeholder for Phase 3+
-- See docs/development_brief.md §21 for situations, channels, tones, base lists.

insert into locale_variants(id, country, region, label, default_formality, pronoun_policy, notes)
values
('es-UY-montevideo', 'Uruguay', 'Montevideo', 'Uruguayan Spanish / Montevideo', 'polite_neutral', 'vos default where natural; ustedes plural', 'MVP default locale. Avoid Spain-specific output and excessive Buenos Aires slang.')
on conflict (id) do nothing;
