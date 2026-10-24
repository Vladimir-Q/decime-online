Extract MVP training candidates from the Spanish text.
Extract only these item types: noun, adjective, verb_form, verb_infinitive.
Do not extract full expressions, idioms, sentence patterns, or complete replies in MVP.

Rules:
- For nouns, include article, gender, number, lemma, RU/EN translations.
- For adjectives, include gender, number and common forms if relevant.
- For verbs, extract the exact observed surface form as a separate item.
- A verb form is not the same as its infinitive.
- Include display_text with pronoun when useful: "vos podés", "yo voy".
- Include lemma, person, number, tense, mood, voseo flag if relevant.
- Include governance/preposition patterns when known.
- Include exact and contextual translations in Russian and English.
- Use the source Spanish sentence as example_es.
- Avoid private data, names, addresses, phone numbers.
- Use locale_variant exactly: es-UY-montevideo (not es-UY).
