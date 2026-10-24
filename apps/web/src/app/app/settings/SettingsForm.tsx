"use client";

import { useEffect, useState } from "react";

import { AppNav } from "@/components/AppNav";
import { useAppLanguage } from "@/components/AppLanguageProvider";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { fetchAuthConfig, logout } from "@/lib/auth";
import { saveAppLanguage, ui, type AppLanguage } from "@/lib/app-language";

export function SettingsForm() {
  const { language, setLanguage, t } = useAppLanguage();
  const [appLanguageDraft, setAppLanguageDraft] = useState<AppLanguage>(language);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setAppLanguageDraft(language);
  }, [language]);

  useEffect(() => {
    void (async () => {
      const config = await fetchAuthConfig();
      setAuthEnabled(config.auth_enabled);
    })();
  }, []);

  async function handleSaveLanguage() {
    setBusy(true);
    setError(null);
    setStatusMessage(null);
    try {
      await saveAppLanguage(appLanguageDraft);
      setLanguage(appLanguageDraft);
      setStatusMessage(
        appLanguageDraft === "en" ? ui("en").languageSaved : ui("ru").languageSaved,
      );
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save language");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <AppNav />
      <section className="hero">
        <p className="eyebrow">{t.settingsTitle}</p>
        <h1>{t.settingsTitle}</h1>
        <p className="lead">{t.settingsLead}</p>
      </section>

      <section className="card settings-section">
        <h2>{t.languageLabel}</h2>
        <select
          id="app-language"
          className="select"
          value={appLanguageDraft}
          onChange={(event) => setAppLanguageDraft(event.target.value as AppLanguage)}
        >
          <option value="ru">Русский</option>
          <option value="en">English</option>
        </select>
        <div className="settings-actions">
          <button
            type="button"
            className="button primary"
            disabled={busy || appLanguageDraft === language}
            onClick={() => void handleSaveLanguage()}
          >
            {t.saveLanguage}
          </button>
        </div>
      </section>

      {authEnabled ? (
        <section className="card settings-section">
          <button
            type="button"
            className="button secondary"
            onClick={() => {
              void logout().then(() => {
                window.location.href = "/login/";
              });
            }}
          >
            {t.logout}
          </button>
          {!isCapacitorMobileBuild() ? (
            <p className="muted" style={{ marginTop: "0.75rem" }}>
              <a href="/app/admin/users/">{t.navAdminUsers}</a>
              {" · "}
              <a href="/app/admin/ai/">{t.navAdminAi}</a>
              {" · "}
              <a href="/app/admin/usage/">{t.navAdminUsage}</a>
            </p>
          ) : null}
        </section>
      ) : null}

      {statusMessage ? <p className="status-ok">{statusMessage}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </main>
  );
}
