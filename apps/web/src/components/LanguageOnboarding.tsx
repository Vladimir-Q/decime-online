"use client";

import { useState } from "react";

import type { AppLanguage } from "@/lib/app-language";
import { saveAppLanguage, ui } from "@/lib/app-language";

interface LanguageOnboardingProps {
  onChosen: (language: AppLanguage) => void;
}

export function LanguageOnboarding({ onChosen }: LanguageOnboardingProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Show bilingual chrome until chosen.
  const copy = ui("ru");

  async function choose(language: AppLanguage) {
    setBusy(true);
    setError(null);
    try {
      await saveAppLanguage(language);
      onChosen(language);
    } catch (chooseError) {
      setError(chooseError instanceof Error ? chooseError.message : "Could not save language");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <section className="card settings-section language-onboarding">
        <h1>{copy.chooseLanguageTitle} / Choose language</h1>
        <p className="muted">{copy.chooseLanguageLead}</p>
        <div className="actions">
          <button
            type="button"
            className="button primary"
            disabled={busy}
            onClick={() => void choose("ru")}
          >
            {copy.chooseRussian}
          </button>
          <button
            type="button"
            className="button secondary"
            disabled={busy}
            onClick={() => void choose("en")}
          >
            {ui("en").chooseEnglish}
          </button>
        </div>
        {error ? <p className="error">{error}</p> : null}
      </section>
    </main>
  );
}
