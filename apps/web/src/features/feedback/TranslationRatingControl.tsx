"use client";

import { useState } from "react";

import { useAppLanguage } from "@/components/AppLanguageProvider";
import { submitTranslationRating } from "@/lib/api";

interface TranslationRatingControlProps {
  feature: "quick_reply" | "live_chat";
  sourceText?: string;
  resultText?: string;
  direction?: string;
}

export function TranslationRatingControl({
  feature,
  sourceText,
  resultText,
  direction,
}: TranslationRatingControlProps) {
  const { t } = useAppLanguage();
  const [saved, setSaved] = useState<-1 | 0 | 1 | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function rate(rating: -1 | 0 | 1) {
    if (busy) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await submitTranslationRating({
        feature,
        rating,
        source_text: sourceText,
        result_text: resultText,
        direction,
      });
      setSaved(rating);
    } catch (rateError) {
      setError(rateError instanceof Error ? rateError.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="translation-rating">
      <p className="muted rating-label">{t.ratingLabel}</p>
      <div className="rating-actions">
        <button
          type="button"
          className={`button small ${saved === 1 ? "primary" : "secondary"}`}
          disabled={busy || saved !== null}
          onClick={() => void rate(1)}
        >
          {t.ratingGood}
        </button>
        <button
          type="button"
          className={`button small ${saved === 0 ? "primary" : "secondary"}`}
          disabled={busy || saved !== null}
          onClick={() => void rate(0)}
        >
          {t.ratingMixed}
        </button>
        <button
          type="button"
          className={`button small ${saved === -1 ? "primary" : "secondary"}`}
          disabled={busy || saved !== null}
          onClick={() => void rate(-1)}
        >
          {t.ratingBad}
        </button>
      </div>
      {error ? <p className="error small-msg">{error}</p> : null}
    </div>
  );
}
