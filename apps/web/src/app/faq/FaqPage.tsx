"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getCachedAppLanguage, ui, type AppLanguage } from "@/lib/app-language";

const FAQ_ITEMS = [
  ["faqQ1", "faqA1"],
  ["faqQ2", "faqA2"],
  ["faqQ3", "faqA3"],
  ["faqQ4", "faqA4"],
  ["faqQ5", "faqA5"],
] as const;

export function FaqPage() {
  const [language, setLanguage] = useState<AppLanguage>("ru");
  const [ready, setReady] = useState(false);
  const t = ui(language);

  useEffect(() => {
    let cancelled = false;
    void getCachedAppLanguage().then((cached) => {
      if (!cancelled) {
        if (cached) {
          setLanguage(cached);
        }
        setReady(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return (
      <main className="page">
        <p className="muted">…</p>
      </main>
    );
  }

  return (
    <main className="page faq-page">
      <section className="hero">
        <p className="eyebrow">Decime UY</p>
        <h1>{t.faqTitle}</h1>
        <p className="lead">{t.faqLead}</p>
        <Link className="button secondary" href="/">
          {t.faqBackHome}
        </Link>
      </section>

      <div className="faq-list">
        {FAQ_ITEMS.map(([qKey, aKey]) => (
          <article key={qKey} className="card faq-item">
            <h2>{t[qKey]}</h2>
            <p>{t[aKey]}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
