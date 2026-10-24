export type LiveInputLanguage = "es" | "ru" | "en";

export type LiveDirection = "to_es" | "to_explanation";

export type AppLanguage = "ru" | "en";

const CYRILLIC = /[\u0400-\u04FF]/;
const LATIN = /[A-Za-zÀ-ÿ]/;
const SPANISH_MARKERS = /[¿¡]|[áéíóúñü]/i;
const SPANISH_SUFFIX =
  /(?:ción|sión|dad|tad|mente|ando|iendo|amos|emos|imos|áis|éis|ís)\b/i;

/** High-signal Spanish tokens that often appear without diacritics. */
const SPANISH_CUES = new Set(
  [
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "del",
    "al",
    "de",
    "en",
    "con",
    "por",
    "para",
    "que",
    "qué",
    "como",
    "cómo",
    "donde",
    "dónde",
    "cuando",
    "cuánto",
    "cuanto",
    "porque",
    "también",
    "tambien",
    "muy",
    "hay",
    "está",
    "esta",
    "están",
    "estan",
    "soy",
    "eres",
    "somos",
    "tengo",
    "tiene",
    "tenemos",
    "quiero",
    "quiere",
    "puedo",
    "puede",
    "necesito",
    "necesita",
    "hacer",
    "pagar",
    "pago",
    "tarjeta",
    "efectivo",
    "gracias",
    "hola",
    "buenos",
    "buenas",
    "días",
    "dias",
    "favor",
    "porfa",
    "sí",
    "si",
    "no",
    "más",
    "mas",
    "menos",
    "hoy",
    "mañana",
    "manana",
    "ahora",
    "después",
    "despues",
    "aquí",
    "aqui",
    "allí",
    "alli",
    "usted",
    "ustedes",
    "vos",
    "che",
  ].map((word) => word.toLowerCase()),
);

/** High-signal English tokens for EN↔ES disambiguation. */
const ENGLISH_CUES = new Set(
  [
    "the",
    "a",
    "an",
    "is",
    "are",
    "am",
    "was",
    "were",
    "be",
    "been",
    "i",
    "you",
    "we",
    "they",
    "he",
    "she",
    "it",
    "my",
    "your",
    "our",
    "their",
    "this",
    "that",
    "these",
    "those",
    "can",
    "could",
    "would",
    "should",
    "need",
    "want",
    "have",
    "has",
    "do",
    "does",
    "did",
    "please",
    "thanks",
    "thank",
    "hello",
    "hi",
    "pay",
    "card",
    "cash",
    "with",
    "without",
    "from",
    "into",
    "about",
    "because",
    "where",
    "when",
    "what",
    "how",
    "why",
  ].map((word) => word.toLowerCase()),
);

function letterStats(text: string): { letters: number; cyrillic: number; latin: number } {
  let letters = 0;
  let cyrillic = 0;
  let latin = 0;
  for (const char of text) {
    if (CYRILLIC.test(char)) {
      letters += 1;
      cyrillic += 1;
    } else if (LATIN.test(char)) {
      letters += 1;
      latin += 1;
    }
  }
  return { letters, cyrillic, latin };
}

function tokenizeLatin(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-zà-ÿáéíóúñü]+/i)
    .filter((token) => token.length > 0);
}

function spanishCueScore(text: string): number {
  let score = 0;
  if (SPANISH_MARKERS.test(text)) {
    score += 3;
  }
  for (const token of tokenizeLatin(text)) {
    if (SPANISH_CUES.has(token)) {
      score += 1;
    }
    if (SPANISH_SUFFIX.test(token) && token.length >= 5) {
      score += 1;
    }
  }
  return score;
}

function englishCueScore(text: string): number {
  let score = 0;
  for (const token of tokenizeLatin(text)) {
    if (ENGLISH_CUES.has(token)) {
      score += 1;
    }
  }
  return score;
}

export function isMostlyCyrillic(text: string): boolean {
  const { letters, cyrillic } = letterStats(text);
  if (letters === 0) {
    return false;
  }
  return cyrillic / letters >= 0.5;
}

export function looksLikeSpanish(text: string): boolean {
  if (SPANISH_MARKERS.test(text)) {
    return true;
  }
  const spanish = spanishCueScore(text);
  if (spanish === 0) {
    return false;
  }
  const english = englishCueScore(text);
  return spanish > english;
}

/** STT hint: auto-detect only within the Live Chat language pair for this UI. */
export function liveSttLanguageHint(appLanguage: AppLanguage): string {
  return appLanguage === "ru" ? "auto:ru,es" : "auto:en,es";
}

/**
 * Live Chat language detection is constrained by app language:
 * - Russian UI: Russian ↔ Spanish only (equal peers)
 * - English UI: English ↔ Spanish only (equal peers)
 */
export function detectInputLanguage(
  text: string,
  appLanguage: AppLanguage = "en",
): LiveInputLanguage {
  const trimmed = text.trim();
  if (!trimmed) {
    return appLanguage;
  }

  if (appLanguage === "ru") {
    return isMostlyCyrillic(trimmed) ? "ru" : "es";
  }

  // English UI: Spanish markers/cues → es, otherwise English (no Russian path).
  if (looksLikeSpanish(trimmed)) {
    return "es";
  }
  return "en";
}

/**
 * Resolve language from text + optional STT hint, still constrained by app language.
 * Russian and Spanish are equal: Cyrillic → ru, otherwise → es in RU UI.
 */
export function resolveLiveInputLanguage(
  text: string,
  appLanguage: AppLanguage,
  hinted?: string | null,
): LiveInputLanguage {
  const trimmed = text.trim();
  if (!trimmed) {
    return appLanguage;
  }

  const code = (hinted || "").trim().toLowerCase().slice(0, 2);

  if (appLanguage === "ru") {
    if (isMostlyCyrillic(trimmed)) {
      return "ru";
    }
    // Accept STT "es" or any non-Cyrillic as Spanish — do not prefer Russian.
    if (code === "ru" && !isMostlyCyrillic(trimmed)) {
      return "es";
    }
    return "es";
  }

  // English UI — text cues beat a wrong STT "en" on unmarked Spanish.
  if (looksLikeSpanish(trimmed)) {
    return "es";
  }
  if (code === "es") {
    return "es";
  }
  if (code === "ru") {
    // Russian is not a Live Chat option in English UI.
    return "en";
  }
  return "en";
}

export function liveDirectionForLanguage(
  language: LiveInputLanguage,
): LiveDirection {
  return language === "es" ? "to_explanation" : "to_es";
}

export function liveDirectionLabel(
  language: LiveInputLanguage,
  explanationLanguage: "ru" | "en",
  uiLanguage: "ru" | "en" = explanationLanguage,
): string {
  const ru = uiLanguage === "ru";
  if (language === "es") {
    if (explanationLanguage === "ru") {
      return ru ? "Испанский → русский" : "Spanish → Russian";
    }
    return ru ? "Испанский → английский" : "Spanish → English";
  }
  if (language === "ru") {
    return ru ? "Русский → испанский (Уругвай)" : "Russian → Spanish (Uruguay)";
  }
  return ru ? "Английский → испанский (Уругвай)" : "English → Spanish (Uruguay)";
}
