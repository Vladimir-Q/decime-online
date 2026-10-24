export type RatingFeature = "quick_reply" | "live_chat";
export type RatingValue = -1 | 0 | 1;

export interface TranslationRatingRequest {
  feature: RatingFeature;
  rating: RatingValue;
  source_text?: string | null;
  result_text?: string | null;
  direction?: string | null;
}

export interface TranslationRatingResponse {
  rating_id: string;
  feature: RatingFeature;
  rating: RatingValue;
}
