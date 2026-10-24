"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  getCachedAppLanguage,
  setCachedAppLanguage,
  ui,
  type AppLanguage,
} from "@/lib/app-language";
import { APP_VERSION } from "@/lib/app-version";

export function LandingHome() {
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

  async function switchLanguage(next: AppLanguage) {
    setLanguage(next);
    await setCachedAppLanguage(next);
  }

  if (!ready) {
    return (
      <main className="page landing-page">
        <p className="muted">…</p>
      </main>
    );
  }

  return (
    <main className="page landing-page">
      <section className="hero landing-hero">
        <p className="eyebrow">{t.landingEyebrow}</p>
        <h1>{t.landingTitle}</h1>
        <p className="lead">{t.landingLead}</p>
        <p className="landing-version">
          {t.landingVersion} {APP_VERSION}
        </p>
        <div className="actions landing-actions">
          <div className="lang-toggle" role="group" aria-label={t.languageLabel}>
            <button
              type="button"
              className={`chip ${language === "ru" ? "chip-active" : ""}`}
              onClick={() => void switchLanguage("ru")}
            >
              {t.landingLangRu}
            </button>
            <button
              type="button"
              className={`chip ${language === "en" ? "chip-active" : ""}`}
              onClick={() => void switchLanguage("en")}
            >
              {t.landingLangEn}
            </button>
          </div>
          <Link className="button primary" href="/login/?returnTo=%2Fapp%2Flive%2F">
            {t.landingLogin}
          </Link>
          <Link className="button secondary" href="/faq/">
            {t.landingFaq}
          </Link>
        </div>
      </section>
      <p className="app-faq-footer">
        <Link href="/faq/">{t.footerFaq}</Link>
      </p>
    </main>
  );
}
