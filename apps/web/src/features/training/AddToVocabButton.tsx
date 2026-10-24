"use client";

import { useState } from "react";

import { useAppLanguage } from "@/components/AppLanguageProvider";
import { addToVocab } from "@/lib/api";

interface AddToVocabButtonProps {
  spanishText: string;
  sourceLanguage: string;
  sourceOriginalText?: string;
  sourceType?: "generated_reply" | "transcript" | "incoming_text" | "manual";
}

export function AddToVocabButton({
  spanishText,
  sourceLanguage,
  sourceOriginalText,
  sourceType = "generated_reply",
}: AddToVocabButtonProps) {
  const { t } = useAppLanguage();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    const text = spanishText.trim();
    if (!text || busy) {
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await addToVocab({
        spanish_text: text,
        source_language: sourceLanguage,
        source_original_text: sourceOriginalText,
        source_type: sourceType,
      });
      const skipped =
        result.skipped_duplicates.length > 0
          ? ` · ${t.skippedDuplicates}: ${result.skipped_duplicates.length}`
          : "";
      setMessage(`${t.addedToVocab}: ${result.created_items.length}${skipped}`);
    } catch (addError) {
      setError(addError instanceof Error ? addError.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="add-to-vocab">
      <button
        type="button"
        className="button secondary small"
        disabled={busy || !spanishText.trim()}
        onClick={() => void handleClick()}
      >
        {busy ? t.addingToVocab : t.addToVocab}
      </button>
      {message ? <p className="success small-msg">{message}</p> : null}
      {error ? <p className="error small-msg">{error}</p> : null}
    </div>
  );
}
