export interface AdminUsageSummary {
  days: number;
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  known_cost_usd?: number;
  legacy_unverified_cost_usd?: number;
  unknown_price_calls?: number;
  pricing_version?: string | null;
  by_operation: Record<
    string,
    {
      calls: number;
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
      estimated_cost_usd: number;
      unknown_price_calls?: number;
    }
  >;
}

export interface AdminRatingsSummary {
  days: number;
  total: number;
  counts: {
    good: number;
    mixed: number;
    bad: number;
  };
  average_score: number;
  by_feature: Record<string, { good: number; mixed: number; bad: number; total: number }>;
}

export interface AdminDashboardResponse {
  usage: AdminUsageSummary;
  ratings: AdminRatingsSummary;
}
