export type ItemType =
  | "noun"
  | "adjective"
  | "verb_form"
  | "verb_infinitive"
  | "idiom"
  | "expression";

export type CandidateStatusHint =
  | "new"
  | "learning"
  | "known"
  | "ignored"
  | "duplicate_possible";

export interface TrainingCandidate {
  candidate_id: string;
  item_type: ItemType;
  surface_text: string;
  display_text: string;
  lemma?: string | null;
  translations_ru: string[];
  translations_en: string[];
  context_translation_ru?: string | null;
  grammar?: Record<string, unknown>;
  governance?: string[];
  example_es?: string | null;
  status_hint: CandidateStatusHint;
  canonical_key?: string | null;
}

export interface ExtractCandidatesRequest {
  source_type: "generated_reply" | "transcript" | "incoming_text" | "manual";
  source_language: string;
  source_original_text?: string | null;
  spanish_text: string;
  target_locale?: string;
  user_level?: string;
  list_id?: string | null;
}

export interface ExtractCandidatesResponse {
  extraction_id: string;
  candidates: TrainingCandidate[];
}

export interface ApproveCandidatesRequest {
  list_id: string;
  extraction_id: string;
  approved_candidate_ids: string[];
  generate_audio?: boolean;
}

export interface ApproveCandidatesResponse {
  created_items: { item_id: string; surface_text: string; audio_status: string }[];
  skipped_duplicates: string[];
}

export interface TrainingListSummary {
  list_id: string;
  name: string;
  item_count: number;
  due_count?: number;
}

export interface TrainingItemSummary {
  item_id: string;
  list_id: string;
  item_type: ItemType;
  display_text: string;
  translations_ru: string[];
  translations_en: string[];
  example_es?: string | null;
  audio_id?: string | null;
  audio_status: string;
  review_stage?: number;
  next_review_at?: string | null;
  created_at?: string | null;
}

export interface TrainingItemsResponse {
  items: TrainingItemSummary[];
}

export interface AddToVocabRequest {
  spanish_text: string;
  source_language?: string;
  source_original_text?: string | null;
  source_type?: "generated_reply" | "transcript" | "incoming_text" | "manual";
  target_locale?: string;
  list_id?: string | null;
}

export interface AddToVocabResponse {
  created_items: { item_id: string; surface_text: string; audio_status: string }[];
  skipped_duplicates: string[];
  extraction_id: string;
}

export interface ItemAudioResponse {
  item_id: string;
  audio_id: string;
  audio_url: string;
  audio_status: string;
}

export type ReviewMode = "ru_to_es" | "es_to_ru" | "audio_to_meaning" | "grammar_prompt";
export type ReviewGrade = "again" | "hard" | "good" | "easy";

export interface ReviewQueueItem {
  item_id: string;
  item_type: ItemType;
  display_text: string;
  prompt_ru: string;
  prompt_en?: string | null;
  grammar_prompt?: string | null;
  audio_url?: string | null;
  review_modes: ReviewMode[];
  review_stage: number;
}

export interface ReviewNextResponse {
  items: ReviewQueueItem[];
  due_count: number;
}

export interface ReviewSubmitRequest {
  item_id: string;
  review_mode: ReviewMode;
  grade: ReviewGrade;
  response_latency_ms?: number;
  used_hint?: boolean;
}

export interface ReviewSubmitResponse {
  item_id: string;
  review_stage: number;
  next_review_at: string;
  remaining_due: number;
}

export type SheetsJobKind = "export" | "import";
export type SheetsJobStatus = "queued" | "running" | "completed" | "failed";

export interface SheetsJobReport {
  created?: number;
  skipped?: number;
  errors?: number;
  exported_rows?: number | null;
  updated_rows?: number | null;
  row_errors?: Record<string, unknown>[];
  partial?: boolean;
  message?: string | null;
}

export interface SheetsJobAcceptedResponse {
  job_id: string;
  status: SheetsJobStatus;
}

export interface SheetsJobStatusResponse {
  job_id: string;
  kind: SheetsJobKind;
  status: SheetsJobStatus;
  list_id: string;
  spreadsheet_id?: string | null;
  sheet_name?: string | null;
  source_spreadsheet_id?: string | null;
  source_sheet_name?: string | null;
  report: SheetsJobReport;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  finished_at?: string | null;
}
