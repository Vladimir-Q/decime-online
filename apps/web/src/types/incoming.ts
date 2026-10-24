export type TargetExplanationLanguage = "ru" | "en";

export interface UnderstandTextRequest {
  source_text: string;
  source_language?: string;
  target_language?: TargetExplanationLanguage;
  locale_variant?: string;
  channel?: string;
}

export interface UnderstandTextResponse {
  original_text: string;
  translation_ru?: string | null;
  translation_en?: string | null;
  tone_notes_ru?: string[];
  uncertain_parts?: string[];
  detected_locale?: string | null;
}
