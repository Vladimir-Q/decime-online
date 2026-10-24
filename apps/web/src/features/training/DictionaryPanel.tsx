"use client";

import { useCallback, useEffect, useState } from "react";

import { useAppLanguage } from "@/components/AppLanguageProvider";
import { AuthenticatedAudio } from "@/components/AuthenticatedAudio";
import {
  deleteTrainingItem,
  exportDictionaryToSheets,
  fetchTrainingItems,
  fetchTrainingLists,
  generateTrainingItemAudio,
  importDictionaryFromSheets,
  waitForSheetsJob,
} from "@/lib/api";
import type { SheetsJobStatusResponse, TrainingItemSummary } from "@/types/training";

export function DictionaryPanel() {
  const { language, t } = useAppLanguage();
  const [items, setItems] = useState<TrainingItemSummary[]>([]);
  const [listId, setListId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [sheetsBusy, setSheetsBusy] = useState<"export" | "import" | null>(null);
  const [jobInfo, setJobInfo] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [spreadsheetInput, setSpreadsheetInput] = useState("");
  const [sheetNameInput, setSheetNameInput] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const lists = await fetchTrainingLists();
      const defaultList = lists[0];
      if (!defaultList) {
        setItems([]);
        setListId(null);
        return;
      }
      setListId(defaultList.list_id);
      const data = await fetchTrainingItems(defaultList.list_id);
      setItems(data.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load dictionary");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function formatJobResult(job: SheetsJobStatusResponse): string {
    const report = job.report || {};
    if (job.status === "failed") {
      return `${t.dictJobFailed}: ${job.error_message || report.message || "—"}`;
    }
    const parts: string[] = [];
    if (job.kind === "import") {
      parts.push(`${report.created ?? 0} ${t.dictJobCreated}`);
      parts.push(`${report.skipped ?? 0} ${t.dictJobSkipped}`);
      parts.push(`${report.errors ?? 0} ${t.dictJobErrors}`);
      const label = report.partial ? t.dictJobPartial : t.dictJobCompleted;
      return `${label}: ${parts.join(", ")}`;
    }
    const exported = report.exported_rows ?? report.updated_rows;
    if (exported != null) {
      return `${t.dictJobCompleted}: ${exported}`;
    }
    return report.message || t.dictJobCompleted;
  }

  async function runSheetsJob(
    kind: "export" | "import",
    start: () => Promise<{ job_id: string }>,
  ) {
    setSheetsBusy(kind);
    setError(null);
    setJobInfo(t.dictJobRunning);
    try {
      const accepted = await start();
      const job = await waitForSheetsJob(accepted.job_id);
      setJobInfo(formatJobResult(job));
      if (kind === "import" && job.status === "completed") {
        await load();
      }
      if (job.status === "failed") {
        setError(job.error_message || t.dictJobFailed);
      }
    } catch (jobError) {
      setJobInfo(null);
      setError(jobError instanceof Error ? jobError.message : t.dictJobFailed);
    } finally {
      setSheetsBusy(null);
    }
  }

  async function handleExport() {
    if (!listId) {
      return;
    }
    await runSheetsJob("export", () => exportDictionaryToSheets(listId));
  }

  async function handleImportSubmit() {
    if (!listId) {
      return;
    }
    const source_spreadsheet_id = spreadsheetInput.trim();
    const source_sheet_name = sheetNameInput.trim();
    if (!source_spreadsheet_id || !source_sheet_name) {
      setError("Укажите таблицу и вкладку");
      return;
    }
    setShowImport(false);
    await runSheetsJob("import", () =>
      importDictionaryFromSheets({
        list_id: listId,
        source_spreadsheet_id,
        source_sheet_name,
      }),
    );
  }

  async function handleSpeak(item: TrainingItemSummary) {
    setBusyId(item.item_id);
    setError(null);
    try {
      const result = await generateTrainingItemAudio(item.item_id, {
        text: item.display_text,
      });
      setItems((current) =>
        current.map((row) =>
          row.item_id === item.item_id
            ? { ...row, audio_id: result.audio_id, audio_status: result.audio_status }
            : row,
        ),
      );
    } catch (speakError) {
      setError(speakError instanceof Error ? speakError.message : "TTS failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(item: TrainingItemSummary) {
    setBusyId(item.item_id);
    setError(null);
    try {
      await deleteTrainingItem(item.item_id);
      setItems((current) => current.filter((row) => row.item_id !== item.item_id));
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Delete failed");
    } finally {
      setBusyId(null);
    }
  }

  function translationFor(item: TrainingItemSummary): string {
    const preferred = language === "en" ? item.translations_en : item.translations_ru;
    const fallback = language === "en" ? item.translations_ru : item.translations_en;
    return (preferred.length ? preferred : fallback).join(", ") || "—";
  }

  const showSheets = language === "ru";

  return (
    <section className="card training-dict">
      <div className="actions">
        <button type="button" className="button secondary" onClick={() => void load()} disabled={loading}>
          {t.refresh}
        </button>
        {showSheets ? (
          <>
            <button
              type="button"
              className="button secondary"
              disabled={!listId || sheetsBusy !== null || loading}
              onClick={() => void handleExport()}
            >
              {sheetsBusy === "export" ? t.dictExporting : t.dictExportSheets}
            </button>
            <button
              type="button"
              className="button secondary"
              disabled={!listId || sheetsBusy !== null || loading}
              onClick={() => setShowImport((open) => !open)}
            >
              {sheetsBusy === "import" ? t.dictImporting : t.dictImportSheets}
            </button>
          </>
        ) : null}
        {listId ? (
          <p className="muted">
            {items.length} {t.dictCount}
          </p>
        ) : null}
      </div>
      {showSheets && showImport ? (
        <div className="dict-import-form">
          <h3>{t.dictImportTitle}</h3>
          <label>
            {t.dictImportSpreadsheet}
            <input
              type="text"
              value={spreadsheetInput}
              onChange={(event) => setSpreadsheetInput(event.target.value)}
              placeholder="1FkTZ0… or https://docs.google.com/spreadsheets/d/…"
            />
          </label>
          <label>
            {t.dictImportSheetName}
            <input
              type="text"
              value={sheetNameInput}
              onChange={(event) => setSheetNameInput(event.target.value)}
              placeholder="Sheet1"
            />
          </label>
          <div className="actions">
            <button
              type="button"
              className="button"
              disabled={sheetsBusy !== null}
              onClick={() => void handleImportSubmit()}
            >
              {t.dictImportSubmit}
            </button>
            <button
              type="button"
              className="button secondary"
              onClick={() => setShowImport(false)}
            >
              {t.dictImportCancel}
            </button>
          </div>
        </div>
      ) : null}
      {loading ? <p className="muted">{t.loading}</p> : null}
      {jobInfo ? <p className="muted">{jobInfo}</p> : null}
      {error ? <p className="error">{error}</p> : null}
      {!loading && items.length === 0 ? <p className="muted">{t.dictEmpty}</p> : null}
      <ul className="dict-list">
        {items.map((item) => (
          <li key={item.item_id} className="dict-row">
            <div className="dict-main">
              <span className="candidate-type">{item.item_type}</span>
              <strong>{item.display_text}</strong>
              <span className="candidate-translations">{translationFor(item)}</span>
              {item.example_es ? <p className="candidate-example">{item.example_es}</p> : null}
              {item.audio_id ? (
                <AuthenticatedAudio
                  url={`/api/v1/audio/files/${item.audio_id}`}
                  className="audio-element"
                />
              ) : null}
            </div>
            <div className="dict-actions">
              {!item.audio_id ? (
                <button
                  type="button"
                  className="button secondary small"
                  disabled={busyId === item.item_id}
                  onClick={() => void handleSpeak(item)}
                >
                  {busyId === item.item_id ? t.speaking : t.speak}
                </button>
              ) : null}
              <button
                type="button"
                className="button secondary small"
                disabled={busyId === item.item_id}
                onClick={() => void handleDelete(item)}
              >
                {busyId === item.item_id ? t.deleting : t.delete}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
