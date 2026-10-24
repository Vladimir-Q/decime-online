"use client";

import { useEffect, useState } from "react";

import { understandIncomingText } from "@/lib/api";
import { getApiBaseUrl, isLoopbackApiUrl, probeDecimeHealth } from "@/lib/api-config";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { canUseNativeApiSetup, openNativeApiSetup } from "@/lib/decime-api-native";
import { isNativePlatform } from "@/lib/native-share";

export function ApiDiagnosticsPanel() {
  const mobileShell = isCapacitorMobileBuild() || isNativePlatform();
  const [apiUrl, setApiUrl] = useState("");
  const [healthLine, setHealthLine] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refreshStatus() {
    const current = await getApiBaseUrl();
    setApiUrl(current);
    if (!current || isLoopbackApiUrl(current)) {
      setHealthLine(null);
      setError(
        !current
          ? "API не задан. Укажите http://192.168.x.x:8000 ниже или через «Изменить IP»."
          : "Сейчас localhost — на телефоне не работает.",
      );
      return;
    }

    try {
      const health = await probeDecimeHealth(current);
      setHealthLine(`Health OK: ${health.app} · ${health.env ?? health.status ?? "local"}`);
      setError(null);
    } catch (probeError) {
      setHealthLine(null);
      setError(probeError instanceof Error ? probeError.message : "Нет связи с API");
    }
  }

  useEffect(() => {
    if (!mobileShell) {
      return;
    }
    void refreshStatus();
    const onApiUrl = () => {
      void refreshStatus();
    };
    window.addEventListener("decime-api-url", onApiUrl);
    return () => window.removeEventListener("decime-api-url", onApiUrl);
  }, [mobileShell]);

  async function handleTestTranslate() {
    setBusy(true);
    setError(null);
    setHealthLine(null);
    try {
      const result = await understandIncomingText({
        source_text: "Hola, como estas?",
        source_language: "es",
        target_language: "ru",
        locale_variant: "es-UY-montevideo",
        channel: "whatsapp_text",
      });
      setHealthLine(
        `Translate OK: ${result.translation_ru || result.translation_en || "ответ получен"}`,
      );
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : "Translate test failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleChangeIp() {
    setBusy(true);
    try {
      await openNativeApiSetup();
      await refreshStatus();
    } finally {
      setBusy(false);
    }
  }

  if (!mobileShell) {
    return (
      <section className="card settings-section">
        <p className="muted">Диагностика API доступна в мобильной сборке (Capacitor).</p>
      </section>
    );
  }

  return (
    <section className="card settings-section api-diagnostics-panel">
      <h2>Статус API</h2>
      <div className="api-status-row">
        <strong>URL:</strong>
        <code>{apiUrl || "не задан"}</code>
      </div>
      {healthLine ? <p className="status-ok">{healthLine}</p> : null}
      {error ? <p className="error">{error}</p> : null}
      <div className="settings-actions">
        <button type="button" className="button secondary small" disabled={busy} onClick={() => void refreshStatus()}>
          {busy ? "..." : "Проверить health"}
        </button>
        {canUseNativeApiSetup() ? (
          <>
            <button type="button" className="button secondary small" disabled={busy} onClick={() => void handleChangeIp()}>
              {busy ? "..." : "Изменить IP"}
            </button>
            <button type="button" className="button primary small" disabled={busy} onClick={() => void handleTestTranslate()}>
              {busy ? "..." : "Тест Translate"}
            </button>
          </>
        ) : null}
      </div>
    </section>
  );
}
