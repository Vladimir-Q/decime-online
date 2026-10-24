"use client";

import { useEffect, useState } from "react";

import { AppNav } from "@/components/AppNav";
import { useAppLanguage } from "@/components/AppLanguageProvider";
import { HistoryList } from "@/features/history/HistoryList";
import { DictionaryPanel } from "@/features/training/DictionaryPanel";
import { TrainingReviewPanel } from "@/features/training/TrainingReviewPanel";
import { clearHistory, fetchHistory, fetchTrainingLists } from "@/lib/api";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import type { HistoryItem } from "@/types/compose";

type TrainingTab = "dictionary" | "history" | "review";

function parseTab(value: string | null): TrainingTab {
  if (value === "history" || value === "review") {
    return value;
  }
  return "dictionary";
}

export default function TrainingPage() {
  const { t } = useAppLanguage();
  const mobileShell = isCapacitorMobileBuild();
  const [tab, setTab] = useState<TrainingTab>("dictionary");
  const [dueCount, setDueCount] = useState(0);
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setTab(parseTab(params.get("tab")));
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const lists = await fetchTrainingLists();
        setDueCount(lists[0]?.due_count ?? 0);
      } catch {
        setDueCount(0);
      }
    })();
  }, [tab]);

  useEffect(() => {
    if (tab !== "history") {
      return;
    }
    void (async () => {
      setHistoryLoading(true);
      setHistoryError(null);
      try {
        const history = await fetchHistory();
        setHistoryItems(history.items);
      } catch (error) {
        setHistoryError(error instanceof Error ? error.message : "Could not load history");
      } finally {
        setHistoryLoading(false);
      }
    })();
  }, [tab]);

  async function handleClearHistory() {
    setClearing(true);
    setHistoryError(null);
    try {
      await clearHistory();
      setHistoryItems([]);
    } catch (error) {
      setHistoryError(error instanceof Error ? error.message : "Clear failed");
    } finally {
      setClearing(false);
    }
  }

  function selectTab(next: TrainingTab) {
    setTab(next);
    const url = new URL(window.location.href);
    if (next === "dictionary") {
      url.searchParams.delete("tab");
    } else {
      url.searchParams.set("tab", next);
    }
    window.history.replaceState({}, "", url.toString());
  }

  return (
    <main className="page page-training">
      <AppNav variant={mobileShell ? "compact" : "full"} />
      <section className="hero">
        <p className="eyebrow">{t.navTraining}</p>
        {!mobileShell ? <p className="lead">{t.trainingLead}</p> : null}
        <div className="training-tabs">
          <button
            type="button"
            className={`button small ${tab === "dictionary" ? "primary" : "secondary"}`}
            onClick={() => selectTab("dictionary")}
          >
            {t.dictTab}
          </button>
          <button
            type="button"
            className={`button small ${tab === "history" ? "primary" : "secondary"}`}
            onClick={() => selectTab("history")}
          >
            {t.historyTab}
          </button>
          <button
            type="button"
            className={`button small ${tab === "review" ? "primary" : "secondary"}`}
            onClick={() => selectTab("review")}
          >
            {t.reviewTab}
            {dueCount ? ` (${dueCount})` : ""}
          </button>
        </div>
      </section>

      {tab === "dictionary" ? <DictionaryPanel /> : null}

      {tab === "history" ? (
        <section className="card">
          <div className="actions">
            <button
              type="button"
              className="button secondary"
              disabled={clearing || historyItems.length === 0}
              onClick={() => void handleClearHistory()}
            >
              {clearing ? t.clearing : t.clearHistory}
            </button>
          </div>
          {historyLoading ? <p className="muted">{t.loading}</p> : null}
          {historyError ? <p className="error">{historyError}</p> : null}
          {!historyLoading && !historyError ? <HistoryList items={historyItems} /> : null}
        </section>
      ) : null}

      {tab === "review" ? (
        <TrainingReviewPanel onDueCountChange={setDueCount} />
      ) : null}
    </main>
  );
}
