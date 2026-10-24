"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AuthenticatedAudio } from "@/components/AuthenticatedAudio";
import { useAppLanguage } from "@/components/AppLanguageProvider";
import { fetchReviewNext, fetchTrainingLists, submitReview } from "@/lib/api";
import type { ReviewGrade, ReviewMode, ReviewQueueItem } from "@/types/training";

const MODE_LABELS_EN: Record<ReviewMode, string> = {
  ru_to_es: "EN → ES",
  es_to_ru: "ES → EN",
  audio_to_meaning: "Audio",
  grammar_prompt: "Grammar",
};

const MODE_LABELS_RU: Record<ReviewMode, string> = {
  ru_to_es: "RU → ES",
  es_to_ru: "ES → RU",
  audio_to_meaning: "Аудио",
  grammar_prompt: "Грамматика",
};

function pickDefaultMode(item: ReviewQueueItem): ReviewMode {
  return item.review_modes[0] ?? "ru_to_es";
}

function meaningPrompt(item: ReviewQueueItem, appLanguage: "ru" | "en"): string {
  if (appLanguage === "en") {
    return item.prompt_en?.trim() || item.prompt_ru;
  }
  return item.prompt_ru;
}

function meaningAnswer(item: ReviewQueueItem, appLanguage: "ru" | "en"): string {
  if (appLanguage === "en") {
    return item.prompt_en?.trim() || item.prompt_ru;
  }
  return [item.prompt_ru, item.prompt_en].filter(Boolean).join(" · ");
}

function buildPrompt(
  item: ReviewQueueItem,
  mode: ReviewMode,
  listenRecall: string,
  appLanguage: "ru" | "en",
): string {
  switch (mode) {
    case "ru_to_es":
      return meaningPrompt(item, appLanguage);
    case "es_to_ru":
      return item.display_text;
    case "audio_to_meaning":
      return listenRecall;
    case "grammar_prompt":
      return `${meaningPrompt(item, appLanguage)} · ${item.grammar_prompt ?? "grammar form"}`;
    default:
      return meaningPrompt(item, appLanguage);
  }
}

function buildAnswer(
  item: ReviewQueueItem,
  mode: ReviewMode,
  appLanguage: "ru" | "en",
): string {
  switch (mode) {
    case "ru_to_es":
      return item.display_text;
    case "es_to_ru":
      return meaningAnswer(item, appLanguage);
    case "audio_to_meaning":
      return meaningAnswer(item, appLanguage);
    case "grammar_prompt":
      return item.display_text;
    default:
      return item.display_text;
  }
}

interface TrainingReviewPanelProps {
  onDueCountChange?: (dueCount: number) => void;
}

export function TrainingReviewPanel({ onDueCountChange }: TrainingReviewPanelProps) {
  const { language, t } = useAppLanguage();
  const [listId, setListId] = useState<string | null>(null);
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [dueCount, setDueCount] = useState(0);
  const [mode, setMode] = useState<ReviewMode>("ru_to_es");
  const [revealed, setRevealed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number>(Date.now());

  const current = queue[0] ?? null;
  const modeLabels = language === "ru" ? MODE_LABELS_RU : MODE_LABELS_EN;

  const publishDueCount = useCallback(
    (next: number) => {
      setDueCount(next);
      onDueCountChange?.(next);
    },
    [onDueCountChange],
  );

  const loadQueue = useCallback(
    async (targetListId: string) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchReviewNext(targetListId, 20);
        setQueue(response.items);
        publishDueCount(response.due_count);
        const first = response.items[0];
        if (first) {
          setMode(pickDefaultMode(first));
          setRevealed(false);
          setStartedAt(Date.now());
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Could not load review queue.");
      } finally {
        setLoading(false);
      }
    },
    [publishDueCount],
  );

  useEffect(() => {
    async function bootstrap() {
      try {
        const lists = await fetchTrainingLists();
        const defaultList = lists[0];
        if (!defaultList) {
          setLoading(false);
          return;
        }
        setListId(defaultList.list_id);
        await loadQueue(defaultList.list_id);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Could not load training lists.");
        setLoading(false);
      }
    }
    void bootstrap();
  }, [loadQueue]);

  const prompt = useMemo(
    () => (current ? buildPrompt(current, mode, t.listenRecall, language) : ""),
    [current, mode, t.listenRecall, language],
  );
  const answer = useMemo(
    () => (current ? buildAnswer(current, mode, language) : ""),
    [current, mode, language],
  );

  async function handleGrade(grade: ReviewGrade) {
    if (!current || !listId || submitting) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await submitReview({
        item_id: current.item_id,
        review_mode: mode,
        grade,
        response_latency_ms: Date.now() - startedAt,
        used_hint: revealed,
      });
      publishDueCount(result.remaining_due);
      setQueue((previous) => previous.slice(1));
      const next = queue[1];
      if (next) {
        setMode(pickDefaultMode(next));
        setRevealed(false);
        setStartedAt(Date.now());
      } else if (result.remaining_due > 0) {
        await loadQueue(listId);
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Review submit failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      {!loading ? (
        <p className="muted">
          {t.reviewDueNow}: {dueCount} · {t.reviewInSession}: {queue.length}
        </p>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
      {loading ? <p className="muted">{t.reviewLoading}</p> : null}

      {!loading && !current ? (
        <section className="card review-card">
          <h2>{t.reviewCaughtUpTitle}</h2>
          <p className="muted">{t.reviewCaughtUpLead}</p>
        </section>
      ) : null}

      {current ? (
        <section className="card review-card">
          <div className="review-meta">
            <span className="candidate-type">{current.item_type}</span>
            <span className="muted">
              {t.stage} {current.review_stage}
            </span>
          </div>

          <div className="review-mode-tabs">
            {current.review_modes.map((reviewMode) => (
              <button
                key={reviewMode}
                type="button"
                className={`button small ${mode === reviewMode ? "primary" : "secondary"}`}
                onClick={() => {
                  setMode(reviewMode);
                  setRevealed(false);
                  setStartedAt(Date.now());
                }}
              >
                {modeLabels[reviewMode]}
              </button>
            ))}
          </div>

          <div className="review-prompt">
            {mode === "audio_to_meaning" && current.audio_url ? (
              <AuthenticatedAudio url={current.audio_url} className="audio-element" />
            ) : (
              <p className="review-prompt-text">{prompt}</p>
            )}
          </div>

          {!revealed ? (
            <button type="button" className="button primary" onClick={() => setRevealed(true)}>
              {t.showAnswer}
            </button>
          ) : (
            <>
              <div className="review-answer">
                <p className="review-answer-label">{t.expected}</p>
                <p className="review-answer-text">{answer}</p>
              </div>
              <div className="review-grades">
                <button
                  type="button"
                  className="button secondary"
                  disabled={submitting}
                  onClick={() => void handleGrade("again")}
                >
                  {t.gradeAgain}
                </button>
                <button
                  type="button"
                  className="button secondary"
                  disabled={submitting}
                  onClick={() => void handleGrade("hard")}
                >
                  {t.gradeHard}
                </button>
                <button
                  type="button"
                  className="button primary"
                  disabled={submitting}
                  onClick={() => void handleGrade("good")}
                >
                  {t.gradeGood}
                </button>
                <button
                  type="button"
                  className="button secondary"
                  disabled={submitting}
                  onClick={() => void handleGrade("easy")}
                >
                  {t.gradeEasy}
                </button>
              </div>
            </>
          )}
        </section>
      ) : null}
    </>
  );
}
