"use client";

import { useAppLanguage } from "@/components/AppLanguageProvider";
import type { HistoryItem } from "@/types/compose";

interface HistoryListProps {
  items: HistoryItem[];
}

export function HistoryList({ items }: HistoryListProps) {
  const { t, language } = useAppLanguage();

  if (items.length === 0) {
    return <p className="muted">{t.historyEmpty}</p>;
  }

  return (
    <div className="history-list">
      {items.map((item) => (
        <article key={item.request_id} className="history-item">
          <div className="history-meta">
            <span>{formatDate(item.created_at, language)}</span>
            {item.channel ? <span>{item.channel}</span> : null}
            {item.provider ? <span>{item.provider}</span> : null}
          </div>
          {item.source_text ? <p className="history-source">{item.source_text}</p> : null}
          <p className="history-reply">{item.recommended_reply}</p>
          {item.dialect_stamp ? <p className="dialect-stamp small">{item.dialect_stamp}</p> : null}
        </article>
      ))}
    </div>
  );
}

function formatDate(value: string, language: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(language === "ru" ? "ru-RU" : "en-US");
}
