"use client";

import { useCallback, useEffect, useState } from "react";

import {
  approveCandidates,
  extractCandidates,
  fetchTrainingLists,
} from "@/lib/api";
import type {
  ApproveCandidatesResponse,
  ExtractCandidatesResponse,
  TrainingCandidate,
} from "@/types/training";

interface TrainingCandidatePanelProps {
  spanishText: string;
  sourceLanguage: string;
  sourceOriginalText?: string;
  onClose: () => void;
  onSaved?: (result: ApproveCandidatesResponse) => void;
}

export function TrainingCandidatePanel({
  spanishText,
  sourceLanguage,
  sourceOriginalText,
  onClose,
  onSaved,
}: TrainingCandidatePanelProps) {
  const [listId, setListId] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<ExtractCandidatesResponse | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [generateAudio, setGenerateAudio] = useState(false);

  const loadExtraction = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSaveMessage(null);
    try {
      const lists = await fetchTrainingLists();
      const defaultList = lists[0];
      if (!defaultList) {
        throw new Error("No training list available");
      }
      setListId(defaultList.list_id);

      const result = await extractCandidates({
        source_type: "generated_reply",
        source_language: sourceLanguage,
        source_original_text: sourceOriginalText,
        spanish_text: spanishText,
        list_id: defaultList.list_id,
      });
      setExtraction(result);
      setSelected(
        new Set(
          result.candidates
            .filter((candidate) => candidate.status_hint !== "duplicate_possible")
            .map((candidate) => candidate.candidate_id)
            .filter((id): id is string => Boolean(id)),
        ),
      );
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : "Extraction failed";
      setError(
        message === "Failed to fetch" || message.includes("Failed to fetch")
          ? "Could not reach the API while extracting words. Wait ~30s and tap Retry."
          : message,
      );
      setExtraction(null);
      setSelected(new Set());
    } finally {
      setLoading(false);
    }
  }, [sourceLanguage, sourceOriginalText, spanishText]);

  useEffect(() => {
    void loadExtraction();
  }, [loadExtraction]);

  function toggleCandidate(candidateId: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(candidateId)) {
        next.delete(candidateId);
      } else {
        next.add(candidateId);
      }
      return next;
    });
  }

  async function handleSave() {
    if (!extraction || !listId || selected.size === 0) {
      return;
    }

    setSaving(true);
    setError(null);
    setSaveMessage(null);
    try {
      const result = await approveCandidates({
        list_id: listId,
        extraction_id: extraction.extraction_id,
        approved_candidate_ids: Array.from(selected),
        generate_audio: generateAudio,
      });
      const skipped =
        result.skipped_duplicates.length > 0
          ? ` Skipped duplicates: ${result.skipped_duplicates.join(", ")}.`
          : "";
      setSaveMessage(`Saved ${result.created_items.length} item(s).${skipped}`);
      onSaved?.(result);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="training-panel">
      <div className="training-panel-header">
        <h3>Add to training</h3>
        <button type="button" className="button secondary small" onClick={onClose}>
          Close
        </button>
      </div>

      <p className="training-source">{spanishText}</p>

        {loading ? <p className="muted">Extracting words… this can take up to 30 seconds.</p> : null}
      {error ? (
        <p className="error">
          {error}{" "}
          <button type="button" className="link-button" onClick={() => void loadExtraction()}>
            Retry
          </button>
        </p>
      ) : null}
      {saveMessage ? <p className="success">{saveMessage}</p> : null}

      {extraction ? (
        <ul className="candidate-list">
          {extraction.candidates.map((candidate) => (
            <CandidateRow
              key={candidate.candidate_id}
              candidate={candidate}
              checked={selected.has(candidate.candidate_id)}
              onToggle={() => toggleCandidate(candidate.candidate_id)}
            />
          ))}
        </ul>
      ) : null}

      <div className="training-actions">
        <label className="training-audio-option">
          <input
            type="checkbox"
            checked={generateAudio}
            onChange={(event) => setGenerateAudio(event.target.checked)}
          />
          Generate pronunciation audio (local Orpheus TTS)
        </label>
        <button
          type="button"
          className="button primary"
          disabled={saving || loading || selected.size === 0}
          onClick={() => void handleSave()}
        >
          {saving ? "Saving..." : `Save selected (${selected.size})`}
        </button>
      </div>
    </section>
  );
}

function CandidateRow({
  candidate,
  checked,
  onToggle,
}: {
  candidate: TrainingCandidate;
  checked: boolean;
  onToggle: () => void;
}) {
  const ru = candidate.translations_ru.join(", ");
  const en = candidate.translations_en.join(", ");
  const isDuplicate = candidate.status_hint === "duplicate_possible";

  return (
    <li className={`candidate-row${isDuplicate ? " duplicate" : ""}`}>
      <label>
        <input
          type="checkbox"
          checked={checked}
          disabled={isDuplicate}
          onChange={onToggle}
        />
        <span className="candidate-type">{candidate.item_type}</span>
        <strong>{candidate.display_text}</strong>
        <span className="candidate-translations">
          {ru}
          {en ? ` · ${en}` : ""}
        </span>
        {isDuplicate ? <span className="candidate-badge">Already in list</span> : null}
      </label>
      {candidate.example_es ? <p className="candidate-example">{candidate.example_es}</p> : null}
    </li>
  );
}
