"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getApiBaseUrl,
  isLoopbackApiUrl,
  probeDecimeHealth,
  scanLanForDecimeApi,
  setApiBaseUrl,
  type LanScanResult,
} from "@/lib/api-config";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { openNativeApiSetup, readNativeNetworkInfo } from "@/lib/decime-api-native";
import { isNativePlatform } from "@/lib/native-share";

function isMobileShell(): boolean {
  return isCapacitorMobileBuild() || isNativePlatform();
}

export function MobileApiConnection() {
  const [draftUrl, setDraftUrl] = useState("");
  const [savedUrl, setSavedUrl] = useState("");
  const [phoneIp, setPhoneIp] = useState("");
  const [subnet, setSubnet] = useState("192.168.1");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanResults, setScanResults] = useState<LanScanResult[]>([]);

  const refresh = useCallback(async () => {
    const current = await getApiBaseUrl();
    setSavedUrl(current);
    if (current && !isLoopbackApiUrl(current)) {
      setDraftUrl(current);
    }
    const network = await readNativeNetworkInfo();
    if (network?.phoneIp) {
      setPhoneIp(network.phoneIp);
    }
    if (network?.subnetPrefix) {
      setSubnet(network.subnetPrefix);
    }
  }, []);

  useEffect(() => {
    if (!isMobileShell()) {
      return;
    }
    void refresh();
    const onUrl = () => {
      void refresh();
    };
    window.addEventListener("decime-api-url", onUrl);
    return () => window.removeEventListener("decime-api-url", onUrl);
  }, [refresh]);

  if (!isMobileShell()) {
    return null;
  }

  async function handleSave() {
    const raw = draftUrl.trim();
    if (!raw) {
      setError("Введите адрес, например http://192.168.1.2:8000");
      return;
    }
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const normalized = await setApiBaseUrl(raw);
      setSavedUrl(normalized);
      setDraftUrl(normalized);
      setStatus(`Сохранено: ${normalized}`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Не удалось сохранить");
    } finally {
      setBusy(false);
    }
  }

  async function handleTest() {
    const url = (savedUrl || draftUrl).trim();
    if (!url) {
      setError("Сначала сохраните URL");
      return;
    }
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const health = await probeDecimeHealth(url);
      setStatus(`Связь OK: ${health.app}`);
    } catch (testError) {
      const message = testError instanceof Error ? testError.message : "Нет связи";
      setError(
        `${message}. На ПК: API с --host 0.0.0.0, разрешите порт 8000 в firewall (см. scripts/allow-decime-firewall.ps1).`,
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleScan() {
    setScanning(true);
    setScanResults([]);
    setError(null);
    setStatus("Ищем Decime API в сети…");
    try {
      const results = await scanLanForDecimeApi({
        subnetPrefix: subnet,
        port: 8000,
        onProgress: (checked, total) => {
          setStatus(`Сканирование ${subnet}.x (${checked}/${total})`);
        },
      });
      setScanResults(results);
      if (results.length === 0) {
        setStatus(null);
        setError("Сервер не найден. Проверьте Wi‑Fi и firewall на ПК.");
        return;
      }
      if (results.length === 1) {
        setDraftUrl(results[0].url);
        const normalized = await setApiBaseUrl(results[0].url);
        setSavedUrl(normalized);
        setStatus(`Найден и сохранён: ${normalized}`);
        return;
      }
      setStatus(`Найдено серверов: ${results.length}. Выберите ниже.`);
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : "Ошибка сканирования");
      setStatus(null);
    } finally {
      setScanning(false);
    }
  }

  async function handlePickResult(result: LanScanResult) {
    setBusy(true);
    setError(null);
    try {
      const normalized = await setApiBaseUrl(result.url);
      setSavedUrl(normalized);
      setDraftUrl(normalized);
      setStatus(`Выбран: ${normalized}`);
    } catch (pickError) {
      setError(pickError instanceof Error ? pickError.message : "Не удалось сохранить");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card settings-section mobile-api-connection">
      <h2>Подключение к ПК</h2>
      <p className="muted">
        Телефон и ПК — одна Wi‑Fi. На ПК запустите API:{" "}
        <code>uvicorn decime_api.main:app --app-dir src --host 0.0.0.0 --port 8000</code>
        {phoneIp ? ` · IP телефона: ${phoneIp}` : null}
      </p>

      <label className="field-label" htmlFor="mobile-api-url">
        Адрес API на ПК
      </label>
      <input
        id="mobile-api-url"
        className="input"
        value={draftUrl}
        onChange={(event) => setDraftUrl(event.target.value)}
        placeholder={`http://${subnet}.2:8000`}
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
      />
      <p className="muted">Сохранено: {savedUrl || "не задано"}</p>

      <div className="settings-actions">
        <button type="button" className="button primary" disabled={busy || scanning} onClick={() => void handleSave()}>
          Сохранить
        </button>
        <button type="button" className="button secondary" disabled={busy || scanning} onClick={() => void handleTest()}>
          Проверить связь
        </button>
        <button type="button" className="button secondary" disabled={busy || scanning} onClick={() => void handleScan()}>
          {scanning ? "Сканирую…" : "Найти в сети"}
        </button>
        <button
          type="button"
          className="button secondary small"
          disabled={busy}
          onClick={() => {
            void openNativeApiSetup().then(() => refresh());
          }}
        >
          Системное окно
        </button>
      </div>

      {scanResults.length > 1 ? (
        <ul className="scan-results">
          {scanResults.map((result) => (
            <li key={result.url}>
              <button
                type="button"
                className="button secondary small"
                disabled={busy}
                onClick={() => void handlePickResult(result)}
              >
                {result.url} — {result.app}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {status ? <p className="status-ok">{status}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
