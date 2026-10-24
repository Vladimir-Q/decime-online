export type Channel = "whatsapp_text" | "in_person";

export type UserLevel = "A1" | "A2" | "B1" | "B2";

export type SourceLanguage = "auto" | "ru" | "en" | "es";

export interface ReplyContext {
  target_locale?: string;
  channel?: Channel;
  user_level?: UserLevel | null;
}

/** RU/EN → es-UY translation request. */
export interface TranslateToEsRequest {
  source_language?: SourceLanguage;
  source_text: string;
  context?: ReplyContext;
}

export interface TranslateToEsResponse {
  request_id: string;
  target_locale: string;
  dialect_stamp: string;
  source_language: string;
  intent_summary_ru: string;
  intent_summary_en?: string | null;
  recommended_reply: string;
  warnings?: string[];
  can_add_to_training?: boolean;
}

export interface HistoryItem {
  request_id: string;
  created_at: string;
  source_language?: string | null;
  source_text?: string | null;
  incoming_text?: string | null;
  channel?: string | null;
  tone?: string | null;
  situation?: string | null;
  recommended_reply: string;
  dialect_stamp?: string | null;
  provider?: string | null;
  model?: string | null;
}

export interface HistoryListResponse {
  items: HistoryItem[];
  total: number;
}

export const CHANNELS = [
  { value: "whatsapp_text" as const, label: "WhatsApp" },
  { value: "in_person" as const, label: "In person" },
];

/** Quick Reply chips: Recommended = null (any), Simple = A2. */
export const QUICK_REPLY_LEVELS = [
  { value: null, labelKey: "toneRecommended" as const },
  { value: "A2" as const, labelKey: "toneSimple" as const },
] as const;
